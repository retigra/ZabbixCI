import logging

from zabbixci.handlers.validation.iconmap_validation import IconMapValidationHandler
from zabbixci.services.icon_map import IconMap
from zabbixci.services.image import Image
from zabbixci.settings import Settings
from zabbixci.zabbix.zabbix import Zabbix

logger = logging.getLogger(__name__)


class IconMapHandler(IconMapValidationHandler):
    """
    Handler for importing images into Zabbix based on changed files. Includes validation steps based on settings.

    :param zabbix: Zabbix instance
    """

    _zabbix: Zabbix

    def __init__(self, zabbix: Zabbix):
        self._zabbix = zabbix

    def icon_map_to_cache(self, images: list[Image]) -> list[IconMap]:
        """
        Export Zabbix icon maps to cache.
        """
        if not Settings.SYNC_ICONMAPS:
            return []

        search = (
            self.get_whitelist()
            if not self._use_regex() and self.get_whitelist()
            else None
        )

        iconmaps = self._zabbix.get_iconmaps(search)

        logger.info(f"Found {len(iconmaps)} iconmap(s) in Zabbix")

        iconmap_objects = []

        for icon_map in iconmaps:
            icon_map_object = IconMap.from_zabbix(icon_map, images)

            if not self.iconmap_validation(icon_map_object):
                continue

            icon_map_object.save()
            iconmap_objects.append(icon_map_object)

        return iconmap_objects

    def import_file_changes(
        self,
        changed_files: list[str],
        iconmap_objects: list[IconMap],
        image_objects: list[Image],
    ) -> list[str]:
        """
        Import icon maps into Zabbix based on changed files.

        :param changed_files: List of changed files
        :param iconmap_objects: List of iconmap objects from Zabbix, needed for choice between creation or update
        :param image_objects: List of image objects from Zabbix,

        :return: List of imported image UUIDs
        """
        icon_maps: list[IconMap] = []

        if not Settings.SYNC_ICONMAPS:
            return []

        for file in changed_files:
            if not self.read_validation(file):
                continue

            iconmap = IconMap.open(file, image_objects)

            if not self.iconmap_validation(iconmap):
                continue

            icon_maps.append(iconmap)
            logger.info(f"Detected change in image: {iconmap.name}")

        # Group images by level
        failed_images: list[Image] = []

        def __import_iconmap(iconmap: IconMap):
            if iconmap.name in [t.name for t in iconmap_objects]:
                logger.info(f"Updating: {iconmap.name}")

                old_iconmap = next(
                    filter(lambda dt: dt.name == iconmap.name, iconmap_objects)
                )

                return self._zabbix.update_iconmap(
                    {
                        "iconmapid": old_iconmap.iconmapid,
                        **iconmap.zabbix_dict,
                    }
                )
            else:
                logger.info(f"Creating: {iconmap.name}")
                return self._zabbix.create_iconmap(iconmap.zabbix_dict)

        # Import the images
        for iconmap in icon_maps:
            if not Settings.DRY_RUN:
                try:
                    __import_iconmap(iconmap)
                except Exception as e:
                    logger.warning(
                        f"Error importing iconmapping {iconmap.name}, will try to import later"
                    )
                    logger.debug(f"Error details: {e}")
                    failed_images.append(iconmap)

        if len(failed_images):
            for image in failed_images:
                try:
                    __import_iconmap(iconmap)
                except Exception as e:
                    logger.error(f"Error importing iconmapping {image}", exc_info=e)

        return [t.name for t in icon_maps]

    def delete_file_changes(
        self,
        deleted_files: list[str],
        imported_iconmap_names: list[str],
        iconmap_objects: list[IconMap],
        image_objects: list[Image],
    ):
        """
        Delete images from Zabbix based on deleted files.

        :param deleted_files: List of deleted files
        :param imported_image_names: List of imported image names
        :param image_objects: List of image objects from Zabbix needed for deletion in current Zabbix instance

        :return: List of deleted image names
        """
        deletion_queue: list[str] = []

        if not Settings.SYNC_ICONS and not Settings.SYNC_BACKGROUNDS:
            return []

        # Check if deleted files are images and if they are imported, if not add to deletion queue
        for file in deleted_files:
            if not self.read_validation(file):
                continue

            iconmap = IconMap.open(file, image_objects)

            if not iconmap:
                logger.warning(f"Could not open to be deleted file: {file}")
                continue

            if not self.iconmap_validation(iconmap):
                continue

            if iconmap.name in imported_iconmap_names:
                logger.debug(
                    f"Iconmap {iconmap.name} was just imported, skipping deletion"
                )
                continue

            deletion_queue.append(iconmap.name)
            logger.info(f"Added {iconmap.name} to deletion queue")

        # Delete images in deletion queue
        if len(deletion_queue):
            iconmap_ids = [
                # Get image IDs from Zabbix
                t.iconmapid
                for t in list(
                    filter(lambda dt: dt.name in deletion_queue, iconmap_objects)
                )
            ]

            logger.info(f"Deleting {len(iconmap_ids)} images from Zabbix")

            if len(iconmap_ids):
                if not Settings.DRY_RUN:
                    self._zabbix.delete_images(iconmap_ids)

        return deletion_queue
