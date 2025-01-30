import logging
import os

from zabbixci.settings import Settings
from zabbixci.utils.cache.filesystem import Filesystem
from zabbixci.utils.handlers.validation.image_validation import ImageValidationHandler
from zabbixci.utils.handlers.validation.template_validation import (
    TemplateValidationHandler,
)
from zabbixci.utils.services.image import Image
from zabbixci.utils.services.template import Template

logger = logging.getLogger(__name__)


class Cleanup:
    @classmethod
    def match_template_cleanup(cls, root: str, name: str):
        if not Settings.SYNC_TEMPLATES:
            return False

        is_template = name.endswith(".yaml") and Filesystem.is_within(
            root, f"{Settings.CACHE_PATH}/{Settings.TEMPLATE_PREFIX_PATH}"
        )

        if not is_template:
            return False

        # Check if the template is in the whitelist
        template_handler = TemplateValidationHandler()

        file = os.path.join(root, name)

        if not template_handler.read_validation(file):
            return False

        template = Template.open(file)

        if not template or not template.is_template:
            logger.warning(f"Could not open file {file} as a template")
            return False

        if not template_handler.template_validation(template):
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

        if not image_handler.image_validation(image):
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
