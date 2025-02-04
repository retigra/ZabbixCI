import asyncio
import logging
from io import StringIO

from ruamel.yaml import YAML

from zabbixci.settings import Settings
from zabbixci.utils.handlers.validation.template_validation import (
    TemplateValidationHandler,
)
from zabbixci.utils.services.template import Template
from zabbixci.utils.zabbix.zabbix import Zabbix

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

        for batchIndex, batch in enumerate(batches):
            logger.info(f"Processing batch {batchIndex + 1}/{len(batches)}")
            coros = []
            for t in batch:
                coros.append(self._zabbix.export_template_async([t["templateid"]]))

            responses = await asyncio.gather(*coros, return_exceptions=True)

            for index, response in enumerate(responses):
                if isinstance(response, BaseException):
                    logger.error(f"Error exporting template: {response}")

                    # Retry the export
                    failed_exports.append(batch[index])
                    continue

                export_yaml = yaml.load(StringIO(response["result"]))

                if "templates" not in export_yaml["zabbix_export"]:
                    logger.info("No templates found in Zabbix")
                    return

                zabbix_template = Template.from_zabbix(export_yaml["zabbix_export"])

                if not self.template_validation(zabbix_template):
                    continue

                zabbix_template.save()
                logger.info(f"Exported Zabbix template {zabbix_template.name}")

        if len(failed_exports):
            logger.warning(
                f"Failed to export {len(failed_exports)} templates, retrying"
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

        logger.info(f"Found {len(templates)} templates in Zabbix")
        logger.debug(f"Found Zabbix templates: {[t['host'] for t in templates]}")

        await self.zabbix_export(templates)
        return templates

    def template_validation(self, template) -> bool:
        """
        Validation steps to perform on a template before it is imported into Zabbix
        """
        if not super().template_validation(template):
            return False

        zabbix_version = self._zabbix.get_server_version()

        if (
            not Settings.IGNORE_TEMPLATE_VERSION
            and template.zabbix_version.split(".")[0:2]
            != zabbix_version.split(".")[0:2]
        ):
            logger.warning(
                f"Template {template.name}: {template.zabbix_version} must match Zabbix release {'.'.join(zabbix_version.split('.')[0:2])}"
            )
            return False

        return True

    def import_file_changes(self, changed_files: list[str]) -> list[str]:
        """
        Import templates into Zabbix based on changed files.
        Changes are parsed and validated before importing.

        :param changed_files: List of changed files

        :return: List of changed template UUIDs
        """
        templates: list[Template] = []

        if Settings.SYNC_TEMPLATES is False:
            return []

        for file in changed_files:
            if not self.read_validation(file):
                continue

            template = Template.open(file)

            if not template or not template.is_template:
                logger.warning(f"Could load file {file} as a template")
                continue

            if not self.template_validation(template):
                continue

            templates.append(template)
            logger.info(f"Detected change in template: {template.name}")

        # Group templates by level
        templates = sorted(templates, key=lambda tl: tl.level(templates))

        failed_templates: list[Template] = []

        # Import the templates
        for template in templates:
            logger.info(f"Importing {template.name}, level {template.level(templates)}")

            if not Settings.DRY_RUN:
                try:
                    self._zabbix.import_template(template)
                except Exception as e:
                    logger.warning(
                        f"Error importing template {template.name}, will try to import later"
                    )
                    logger.debug(f"Error details: {e}")
                    failed_templates.append(template)

        if len(failed_templates):
            for template in failed_templates:
                try:
                    self._zabbix.import_template(template)
                except Exception as e:
                    logger.error(f"Error importing template {template}: {e}")

        return [
            template_id
            for template in templates
            for template_id in template.template_ids
        ]

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
                logger.warning(f"Could not open to be deleted file {file}")
                continue

            if not self.template_validation(template):
                continue

            if template.uuid in imported_template_ids:
                logger.debug(
                    f"Template {template.name} is being imported under a different name or path, skipping deletion"
                )
                continue

            deletion_queue.append(template.name)
            logger.info(f"Added {template.name} to deletion queue")

        # Delete templates in deletion queue
        if len(deletion_queue):
            template_ids = [
                # Get template IDs from Zabbix
                t["templateid"]
                for t in list(
                    filter(lambda dt: dt["host"] in deletion_queue, template_objects)
                )
            ]

            logger.info(f"Deleting {len(template_ids)} templates from Zabbix")

            if len(template_ids):
                if not Settings.DRY_RUN:
                    self._zabbix.delete_templates(template_ids)

        return deletion_queue
