import logging

from zabbixci.assets.icon_map import IconMap
from zabbixci.assets.image import Image
from zabbixci.handlers.validation.icon_map_validation import IconMapValidationHandler
from zabbixci.settings import Settings
from zabbixci.zabbix.zabbix import Zabbix

logger = logging.getLogger(__name__)


class IconMapHandler(IconMapValidationHandler):
    """
    Handler for importing icon maps into Zabbix based on changed files. Includes validation steps based on settings.

    :param zabbix: Zabbix instance
    """

    _zabbix: Zabbix

    def __init__(self, zabbix: Zabbix):
        self._zabbix = zabbix

    def icon_map_to_cache(self, images: list[Image]) -> list[IconMap]:
        """
        Export Zabbix icon maps to cache.
        """
        if not Settings.SYNC_ICON_MAPS:
            return []

        if not Settings.SYNC_ICONS:
            logger.warning(
                "SYNC_ICONS is disabled, unable to export icon maps without icons"
            )
            return []

        search = (
            self.get_whitelist()
            if not self._use_regex() and self.get_whitelist()
            else None
        )

        icon_maps = self._zabbix.get_icon_maps(search)

        logger.info("Found %s icon map(s) in Zabbix", len(icon_maps))

        icon_map_objects = []

        for icon_map in icon_maps:
            icon_map_object = IconMap.from_zabbix(icon_map, images)

            if not self.object_validation(icon_map_object):
                continue

            icon_map_object.save()
            icon_map_objects.append(icon_map_object)

        return icon_map_objects

    def import_file_changes(
        self,
        changed_files: list[str],
        icon_map_objects: list[IconMap],
        image_objects: list[Image],
    ) -> list[str]:
        """
        Import icon maps into Zabbix based on changed files.

        :param changed_files: List of changed files
        :param icon_map_objects: List of icon map objects from Zabbix, needed for choice between creation or update
        :param image_objects: List of image objects from Zabbix, needed to open icon_map exports

        :return: List of imported icon_map names
        """
        icon_maps: list[IconMap] = []

        if not Settings.SYNC_ICON_MAPS:
            return []

        for file in changed_files:
            if not self.read_validation(file):
                continue

            icon_map = IconMap.open(file, image_objects)

            if not self.object_validation(icon_map):
                continue

            icon_maps.append(icon_map)
            logger.info("Detected change in image: %s", icon_map.name)

        def __import_icon_map(icon_map: IconMap):
            if icon_map.name in [t.name for t in icon_map_objects]:
                logger.info("Updating: %s", icon_map.name)

                old_icon_map = next(
                    filter(lambda dt: dt.name == icon_map.name, icon_map_objects)
                )

                return self._zabbix.update_icon_map(
                    {
                        "iconmapid": old_icon_map.icon_mapid,
                        **icon_map.zabbix_dict,
                    }
                )
            else:
                logger.info("Creating: %s", icon_map.name)
                return self._zabbix.create_icon_map(icon_map.zabbix_dict)

        failed_icon_maps: list[IconMap] = []

        # Import the images
        for icon_map in icon_maps:
            if not Settings.DRY_RUN:
                try:
                    __import_icon_map(icon_map)
                except Exception as e:
                    logger.warning(
                        "Error importing icon mapping %s, will try to import later",
                        icon_map.name,
                    )
                    logger.debug("Error details: %s", e)
                    failed_icon_maps.append(icon_map)

        if len(failed_icon_maps):
            for icon_map in failed_icon_maps:
                try:
                    __import_icon_map(icon_map)
                except Exception as e:
                    logger.error(
                        "Error importing icon mapping %s: %s", icon_map.name, e
                    )

        return [t.name for t in icon_maps]

    def delete_file_changes(
        self,
        deleted_files: list[str],
        imported_icon_map_names: list[str],
        icon_map_objects: list[IconMap],
    ):
        """
        Delete icon maps from Zabbix based on deleted files.

        :param deleted_files: List of deleted files
        :param imported_icon_map_names: List of imported icon_map names
        :param icon_map_objects: List of icon_map objects from Zabbix, needed for deletion

        :return: List of deleted image names
        """
        deletion_queue: list[str] = []

        if not Settings.SYNC_ICON_MAPS:
            return []

        for file in deleted_files:
            if not self.read_validation(file):
                continue

            icon_map = IconMap.partial_open(file)

            if not icon_map:
                logger.warning("Could not open to be deleted file: %s", file)
                continue

            if not self.object_validation(icon_map):
                continue

            if icon_map.name in imported_icon_map_names:
                logger.debug(
                    "Icon map %s was just imported, skipping deletion", icon_map.name
                )
                continue

            deletion_queue.append(icon_map.name)
            logger.info("Added %s to deletion queue", icon_map.name)

        if len(deletion_queue):
            icon_map_ids = [
                t.icon_mapid
                for t in list(
                    filter(lambda dt: dt.name in deletion_queue, icon_map_objects)
                )
            ]

            logger.info("Deleting %s icon map(s) from Zabbix", len(icon_map_ids))

            if len(icon_map_ids):
                if not Settings.DRY_RUN:
                    self._zabbix.delete_icon_maps(icon_map_ids)

        return deletion_queue
