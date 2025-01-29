import logging

from zabbixci.settings import Settings
from zabbixci.utils.handlers.validation import Handler

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
