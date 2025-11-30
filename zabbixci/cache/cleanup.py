import logging
import os

from zabbixci.assets.icon_map import IconMap
from zabbixci.assets.image import Image
from zabbixci.assets.script import Script
from zabbixci.assets.template import Template
from zabbixci.handlers.validation.icon_map_validation import IconMapValidationHandler
from zabbixci.handlers.validation.image_validation import ImageValidationHandler
from zabbixci.handlers.validation.script_validation import ScriptValidationHandler
from zabbixci.handlers.validation.template_validation import TemplateValidationHandler
from zabbixci.settings import ApplicationSettings

logger = logging.getLogger(__name__)


class Cleanup:
    @classmethod
    def match_template_cleanup(
        cls, root: str, name: str, settings: ApplicationSettings
    ):
        if not settings.SYNC_TEMPLATES:
            return False

        template_handler = TemplateValidationHandler(settings)
        file = os.path.join(root, name)

        if not template_handler.read_validation(file):
            return False

        template = Template.open(file, settings)

        if not template or not template.is_template:
            logger.warning("Could not open file %s as a template", file)
            return False

        return template_handler.object_validation(template)

    @classmethod
    def match_image_cleanup(cls, root: str, name: str, settings: ApplicationSettings):
        """
        Check if a file is an image file that should be cleaned up
        """
        if not settings.SYNC_ICONS and not settings.SYNC_BACKGROUNDS:
            return False

        image_handler = ImageValidationHandler(settings)

        file = os.path.join(root, name)

        if not image_handler.read_validation(file):
            return False

        image = Image.open(file, settings)

        if not image:
            return False

        return image_handler.object_validation(image)

    @classmethod
    def match_icon_map_cleanup(
        cls, root: str, name: str, settings: ApplicationSettings
    ):
        """
        Check if a file is an icon_map file that should be cleaned up
        """
        if not settings.SYNC_ICON_MAPS:
            return False

        icon_map_handler = IconMapValidationHandler(settings)

        file = os.path.join(root, name)

        if not icon_map_handler.read_validation(file):
            return False

        icon_map = IconMap.partial_open(file, settings)

        if not icon_map_handler:
            return False

        return icon_map_handler.object_validation(icon_map)

    @classmethod
    def match_script_cleanup(cls, root: str, name: str, settings: ApplicationSettings):
        if not settings.SYNC_SCRIPTS:
            return False

        script_handler = ScriptValidationHandler(settings)
        file = os.path.join(root, name)

        if not script_handler.read_validation(file):
            return False

        script = Script.open(file, settings)

        if not script:
            return False

        return script_handler.object_validation(script)

    @classmethod
    def cleanup_cache(cls, settings: ApplicationSettings, full: bool = False) -> None:
        """
        Clean all files in the cache directory that match import/export files

        If full is True, also remove the .git directory and all other files
        """
        for root, dirs, files in os.walk(settings.CACHE_PATH, topdown=False):
            if f"{settings.CACHE_PATH}/.git" in root and not full:
                continue

            for name in files:
                if (
                    full
                    or cls.match_template_cleanup(root, name, settings)
                    or cls.match_image_cleanup(root, name, settings)
                    or cls.match_icon_map_cleanup(root, name, settings)
                    or cls.match_script_cleanup(root, name, settings)
                ):
                    os.remove(os.path.join(root, name))

            for name in dirs:
                if name == ".git" and root == settings.CACHE_PATH and not full:
                    continue

                # Remove empty directories
                if not os.listdir(os.path.join(root, name)):
                    os.rmdir(os.path.join(root, name))

        if full and os.path.exists(settings.CACHE_PATH):
            os.rmdir(settings.CACHE_PATH)
            logger.info("Cache directory cleared")
