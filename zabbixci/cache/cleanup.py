import logging
import os

from zabbixci.assets.icon_map import IconMap
from zabbixci.assets.image import Image
from zabbixci.assets.template import Template
from zabbixci.handlers.validation.icon_map_validation import IconMapValidationHandler
from zabbixci.handlers.validation.image_validation import ImageValidationHandler
from zabbixci.handlers.validation.template_validation import TemplateValidationHandler
from zabbixci.settings import Settings

logger = logging.getLogger(__name__)


class Cleanup:
    @classmethod
    def match_template_cleanup(cls, root: str, name: str):
        if not Settings.SYNC_TEMPLATES:
            return False

        template_handler = TemplateValidationHandler()
        file = os.path.join(root, name)

        if not template_handler.read_validation(file):
            return False

        template = Template.open(file)

        if not template or not template.is_template:
            logger.warning("Could not open file %s as a template", file)
            return False

        if not template_handler.object_validation(template):
            return False

        return True

    @classmethod
    def match_image_cleanup(cls, root: str, name: str):
        """
        Check if a file is an image file that should be cleaned up
        """
        if not Settings.SYNC_ICONS and not Settings.SYNC_BACKGROUNDS:
            return False

        image_handler = ImageValidationHandler()

        file = os.path.join(root, name)

        if not image_handler.read_validation(file):
            return False

        image = Image.open(file)

        if not image:
            return False

        if not image_handler.object_validation(image):
            return False

        return True

    @classmethod
    def match_icon_map_cleanup(cls, root: str, name: str):
        """
        Check if a file is an icon_map file that should be cleaned up
        """
        if not Settings.SYNC_ICON_MAPS:
            return False

        icon_map_handler = IconMapValidationHandler()

        file = os.path.join(root, name)

        if not icon_map_handler.read_validation(file):
            return False

        icon_map = IconMap.partial_open(file)

        if not icon_map_handler:
            return False

        if not icon_map_handler.object_validation(icon_map):
            return False

        return True

    @classmethod
    def cleanup_cache(cls, full: bool = False) -> None:
        """
        Clean all .yaml (template) files from the cache directory

        If full is True, also remove the .git directory and all other files
        """
        for root, dirs, files in os.walk(Settings.CACHE_PATH, topdown=False):
            if f"{Settings.CACHE_PATH}/.git" in root and not full:
                continue

            for name in files:
                if (
                    full
                    or cls.match_template_cleanup(root, name)
                    or cls.match_image_cleanup(root, name)
                    or cls.match_icon_map_cleanup(root, name)
                ):
                    os.remove(os.path.join(root, name))

            for name in dirs:
                if name == ".git" and root == Settings.CACHE_PATH and not full:
                    continue

                # Remove empty directories
                if not os.listdir(os.path.join(root, name)):
                    os.rmdir(os.path.join(root, name))

        if full and os.path.exists(Settings.CACHE_PATH):
            os.rmdir(Settings.CACHE_PATH)
            logger.info("Cache directory cleared")
