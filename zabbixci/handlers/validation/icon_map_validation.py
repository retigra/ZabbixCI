import logging

from zabbixci.assets.icon_map import IconMap
from zabbixci.cache.filesystem import Filesystem
from zabbixci.handlers.validation.validation_handler import Handler
from zabbixci.settings import Settings

logger = logging.getLogger(__name__)


class IconMapValidationHandler(Handler):
    """
    Handler for importing icon maps into Zabbix based on changed files. Includes validation steps based on settings.
    """

    def get_whitelist(self):
        return Settings.get_icon_map_whitelist()

    def get_blacklist(self):
        return Settings.get_icon_map_blacklist()

    def read_validation(self, changed_file: str) -> bool:
        """
        Validation steps to perform on a changed file before it is processed as a icon_map.
        """
        if not changed_file.endswith(".yaml"):
            return False

        # Check if file is within the desired path
        if not Filesystem.is_within(
            changed_file, f"{Settings.CACHE_PATH}/{Settings.ICON_MAP_PREFIX_PATH}"
        ):
            logger.debug(
                f"Skipping .yaml file {changed_file} outside of icon_map prefix path"
            )
            return False

        return True

    def object_validation(self, icon_map: IconMap | None) -> bool:
        if not icon_map:
            return False

        if self.enforce_whitelist(icon_map.name):
            logger.debug(f"Skipping icon_map {icon_map.name} not in whitelist")
            return False

        if self.enforce_blacklist(icon_map.name):
            logger.debug(f"Skipping icon_map {icon_map.name} in blacklist")
            return False

        return True
