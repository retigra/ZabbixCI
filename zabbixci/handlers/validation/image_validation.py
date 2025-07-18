import logging

from zabbixci.assets.image import Image
from zabbixci.cache.filesystem import Filesystem
from zabbixci.handlers.validation.validation_handler import Handler
from zabbixci.settings import Settings

logger = logging.getLogger(__name__)


class ImageValidationHandler(Handler):
    """
    Handler for importing images into Zabbix based on changed files. Includes validation steps based on settings.
    """

    def get_whitelist(self):
        return Settings.get_image_whitelist()

    def get_blacklist(self):
        return Settings.get_image_blacklist()

    def is_image(self, path):
        return path.lower().split(".")[-1] in Settings._DYN_IMG_EXT

    def read_validation(self, changed_file: str) -> bool:
        """
        Validation steps to perform on a changed file before it is processed as a image
        """
        if not self.is_image(changed_file):
            return False

        # Check if file is within the desired path
        if not Filesystem.is_within(
            changed_file, f"{Settings.CACHE_PATH}/{Settings.IMAGE_PREFIX_PATH}"
        ):
            logger.debug("Skipping .png file %s outside of prefix path", changed_file)
            return False

        return True

    def object_validation(self, image: Image | None) -> bool:
        if not image:
            return False

        if not Settings.SYNC_BACKGROUNDS and image.type == "background":
            logger.debug("Skipping background image: %s", image.name)
            return False

        if not Settings.SYNC_ICONS and image.type == "icon":
            logger.debug("Skipping icon image: %s", image.name)
            return False

        if self.enforce_whitelist(image.name):
            logger.debug("Skipping image %s not in whitelist", image.name)
            return False

        if self.enforce_blacklist(image.name):
            logger.debug("Skipping image %s in blacklist", image.name)
            return False

        return True
