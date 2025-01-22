import logging

from zabbixci.settings import Settings
from zabbixci.utils.services.image import Image
from zabbixci.utils.zabbix.zabbix import Zabbix

logger = logging.getLogger(__name__)


class ImageHandler:
    """
    Handler for importing templates into Zabbix based on changed files. Includes validation steps based on settings.

    :param zabbix: Zabbix instance
    """

    _zabbix: Zabbix

    def __init__(self, zabbix: Zabbix):
        self._zabbix = zabbix

    def _read_validation(self, changed_file: str) -> bool:
        """
        Validation steps to perform on a changed file before it is processed as a image
        """
        if not changed_file.endswith(".png"):
            return False

        # Check if file is within the desired path
        if not changed_file.startswith(Settings.IMAGE_PREFIX_PATH):
            logger.debug(f"Skipping .png file {changed_file} outside of prefix path")
            return False

        return True

    def import_file_changes(self, changed_files: list[str]) -> list[str]:
        """
        Import images into Zabbix based on changed files.
        Changes are parsed and validated before importing.

        :param changed_files: List of changed files

        :return: List of imported image UUIDs
        """
        images: list[Image] = []

        for file in changed_files:
            if not self._read_validation(file):
                continue

            image = Image.open(file)

            images.append(image)
            logger.info(f"Detected change in image: {image.name}")

        # Group templates by level
        failed_images: list[Image] = []

        # Import the templates
        for image in images:
            logger.info(f"Importing {image.name}")

            if not Settings.DRY_RUN:
                try:
                    self._zabbix.import_image(image.as_zabbix_dict())
                except Exception as e:
                    logger.warning(
                        f"Error importing image {image.name}, will try to import later"
                    )
                    logger.debug(f"Error details: {e}")
                    failed_images.append(image)

        if len(failed_images):
            for image in failed_images:
                try:
                    self._zabbix.import_image(image.as_zabbix_dict())
                except Exception as e:
                    logger.error(f"Error importing image {image}: {e}")

        return [t.name for t in images]

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
