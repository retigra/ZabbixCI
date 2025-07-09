import asyncio
import logging
from io import StringIO

from ruamel.yaml import YAML
from zabbix_utils import APIRequestError, ProcessingError

from zabbixci.assets.template import Template
from zabbixci.handlers.validation.template_validation import TemplateValidationHandler
from zabbixci.settings import Settings
from zabbixci.zabbix.zabbix import Zabbix

logger = logging.getLogger(__name__)
yaml = YAML()


class TemplateHandler(TemplateValidationHandler):
    """
    Handler for importing templates into Zabbix based on changed files. Includes validation steps based on settings.

    :param zabbix: Zabbix instance
    """

    _zabbix: Zabbix

    def __init__(self, zabbix: Zabbix):
        self._zabbix = zabbix

    async def zabbix_export(self, templates: list[dict]):
        batches = [
            templates[i : i + Settings.BATCH_SIZE]
            for i in range(0, len(templates), Settings.BATCH_SIZE)
        ]

        failed_exports = []

        for batch_index, batch in enumerate(batches):
            logger.info("Processing batch %d/%d", batch_index + 1, len(batches))
            coros = []
            for t in batch:
                coros.append(self._zabbix.export_template_async([t["templateid"]]))

            responses = await asyncio.gather(*coros, return_exceptions=True)

            for index, response in enumerate(responses):
                if isinstance(response, BaseException):
                    logger.warning("Error exporting template: %s", response)

                    # Retry the export
                    failed_exports.append(batch[index])
                    continue

                export_yaml = yaml.load(StringIO(response["result"]))

                if "templates" not in export_yaml["zabbix_export"]:
                    logger.info("No templates found in Zabbix")
                    return

                zabbix_template = Template.from_zabbix(export_yaml["zabbix_export"])

                if not self.object_validation(zabbix_template):
                    continue

                zabbix_template.save()
                logger.info("Exported Zabbix template: %s", zabbix_template.name)

        if failed_exports:
            logger.warning(
                "Failed to export %d %s, retrying",
                len(failed_exports),
                "templates" if (len(failed_exports) > 1) else "template",
            )
            await self.zabbix_export(failed_exports)

    async def templates_to_cache(self) -> list[dict]:
        """
        Export Zabbix templates to the cache
        """
        if not Settings.SYNC_TEMPLATES:
            return []

        search = (
            self.get_whitelist()
            if not self._use_regex() and self.get_whitelist()
            else None
        )
        templates = self._zabbix.get_templates([Settings.ROOT_TEMPLATE_GROUP], search)

        logger.info("Found %d templates in Zabbix", len(templates))
        logger.debug("Found Zabbix templates: %s", [t["host"] for t in templates])

        await self.zabbix_export(templates)
        return templates

    def object_validation(self, template) -> bool:
        """
        Validation steps to perform on a template before it is imported into Zabbix
        """
        if not super().object_validation(template):
            return False

        zabbix_version = self._zabbix.get_server_version()

        if (
            not Settings.IGNORE_TEMPLATE_VERSION
            and template.zabbix_version.split(".")[0:2]
            != zabbix_version.split(".")[0:2]
        ):
            logger.warning(
                "Template %s: %s must match Zabbix release %s",
                template.name,
                template.zabbix_version,
                ".".join(zabbix_version.split(".")[0:2]),
            )
            return False

        return True

    def import_file_changes(
        self, changed_files: list[str]
    ) -> tuple[list[str], list[str]]:
        """
        Import templates into Zabbix based on changed files.
        Changes are parsed and validated before importing.

        :param changed_files: List of changed files

        :return: Tuple of imported template UUIDs and failed template UUIDs
        """
        templates: list[Template] = []

        if Settings.SYNC_TEMPLATES is False:
            return ([], [])

        for file in changed_files:
            if not self.read_validation(file):
                continue

            template = Template.open(file)

            if not template or not template.is_template:
                logger.warning("Could load file %s as a template", file)
                continue

            if not self.object_validation(template):
                continue

            templates.append(template)
            logger.info("Detected change in template: %s", template.name)

        # Group templates by level
        templates = sorted(templates, key=lambda tl: tl.level(templates))

        retry_templates: list[Template] = []
        success_templates: list[str] = []
        failed_templates: list[str] = []

        # Import the templates
        if not Settings.DRY_RUN:
            for template in templates:
                try:
                    logger.info(
                        "Importing %s, level %d",
                        template.name,
                        template.level(templates),
                    )
                    self._zabbix.import_template(template)

                    success_templates.extend(template.template_ids)
                except (APIRequestError, ProcessingError) as e:
                    logger.warning(
                        "Error importing template %s, will try to import later",
                        template.name,
                    )
                    logger.debug("Error details: %s", e)
                    retry_templates.append(template)
        else:
            # Dry-run is enabled, don't import but increment success count
            success_templates.extend(
                [t.template_ids for t in templates if t.template_ids]
            )

        if retry_templates:
            for template in retry_templates:
                try:
                    logger.info(
                        "Importing %s, level %d after previous failure",
                        template.name,
                        template.level(templates),
                    )
                    self._zabbix.import_template(template)

                    success_templates.extend(template.template_ids)
                except (APIRequestError, ProcessingError) as e:
                    logger.error("Error importing template %s: %s", template, e)

                    failed_templates.extend(template.template_ids)

        return (success_templates, failed_templates)

    def delete_file_changes(
        self,
        deleted_files: list[str],
        imported_template_ids: list[str],
        template_objects: list[dict],
    ):
        """
        Delete templates from Zabbix based on deleted files.

        :param deleted_files: List of deleted files
        :param imported_template_ids: List of imported template UUIDs
        :param template_objects: List of template objects from Zabbix needed for deletion in current Zabbix instance

        :return: List of deleted template names
        """
        if Settings.SYNC_TEMPLATES is False:
            return []

        deletion_queue: list[str] = []

        # Check if deleted files are templates and if they are imported, if not add to deletion queue
        for file in deleted_files:
            if not self.read_validation(file):
                continue

            template = Template.open(file)

            if not template or not template.is_template:
                logger.warning("Could not open to be deleted file: %s", file)
                continue

            if not self.object_validation(template):
                continue

            if template.uuid in imported_template_ids:
                logger.debug(
                    "Template %s is being imported under a different name or path, skipping deletion",
                    template.name,
                )
                continue

            deletion_queue.append(template.name)
            logger.info("Added %s to deletion queue", template.name)

        # Delete templates in deletion queue
        if deletion_queue:
            template_ids = [
                # Get template IDs from Zabbix
                t["templateid"]
                for t in list(
                    filter(lambda dt: dt["host"] in deletion_queue, template_objects)
                )
            ]

            logger.info("Deleting %d templates from Zabbix", len(template_ids))

            if len(template_ids):
                if not Settings.DRY_RUN:
                    self._zabbix.delete_templates(template_ids)

        return deletion_queue
