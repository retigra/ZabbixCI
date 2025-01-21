import logging

from zabbixci.settings import Settings
from zabbixci.utils.services.template import Template
from zabbixci.utils.zabbix.zabbix import Zabbix

logger = logging.getLogger(__name__)


class TemplateHandler:
    """
    Handler for importing templates into Zabbix based on changed files. Includes validation steps based on settings.

    :param zabbix: Zabbix instance
    """

    _zabbix: Zabbix

    def __init__(self, zabbix: Zabbix):
        self._zabbix = zabbix

    def _read_validation(self, changed_file: str) -> bool:
        """
        Validation steps to perform on a changed file before it is processed as a template
        """
        if not changed_file.endswith(".yaml"):
            return False

        # Check if file is within the desired path
        if not changed_file.startswith(Settings.TEMPLATE_PREFIX_PATH):
            logger.debug(f"Skipping .yaml file {changed_file} outside of prefix path")
            return False

        return True

    def _template_validation(self, template: Template) -> bool:
        """
        Validation steps to perform on a template before it is imported into Zabbix
        """
        if template.name in Settings.get_template_blacklist():
            logger.debug(f"Skipping blacklisted template {template.name}")
            return False

        if (
            len(Settings.get_template_whitelist())
            and template.name not in Settings.get_template_whitelist()
        ):
            logger.debug(f"Skipping non whitelisted template {template.name}")
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

        for file in changed_files:
            if not self._read_validation(file):
                continue

            template = Template.open(file)

            if not template or not template.is_template:
                logger.warning(f"Could load file {file} as a template")
                continue

            if not self._template_validation(template):
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

        return [t.uuid for t in templates]

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
        deletion_queue: list[str] = []

        # Check if deleted files are templates and if they are imported, if not add to deletion queue
        for file in deleted_files:
            if not self._read_validation(file):
                continue

            template = Template.open(file)

            if not template or not template.is_template:
                logger.warning(f"Could not open to be deleted file {file}")
                continue

            if not self._template_validation(template):
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
                    filter(lambda dt: dt["name"] in deletion_queue, template_objects)
                )
            ]

            logger.info(f"Deleting {len(template_ids)} templates from Zabbix")

            if len(template_ids):
                if not Settings.DRY_RUN:
                    self._zabbix.delete_templates(template_ids)

        return deletion_queue
