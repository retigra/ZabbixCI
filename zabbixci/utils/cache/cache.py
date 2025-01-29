import logging
import os
import os.path

from zabbixci.settings import Settings
from zabbixci.utils.cache.filesystem import Filesystem
from zabbixci.utils.handlers.validation import (
    ImageValidationHandler,
    TemplateValidationHandler,
)


class Cache(Filesystem):
    _instance = None
    _logger = None

    _cache_dir: str = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(Cache, cls).__new__(cls)
            cls._instance.cache = {}
        return cls._instance

    def __init__(self, cache_dir: str):
        self._cache_dir = os.path.realpath(cache_dir)
        self._logger = logging.getLogger(__name__)

    @classmethod
    def _ensure_safe_path(cls, path):
        if not cls.is_within_cache(path):
            raise ValueError(f"Path {path} does not reside within the cache directory")

    @classmethod
    def open(cls, path, mode):
        """
        Wrapped open function that ensures that the path is within the cache directory
        """
        # Binary operations do not take an encoding argument
        if "rb" in mode or "wb" in mode:
            cls._ensure_safe_path(os.path.dirname(path))
            return open(path, mode)

        cls._ensure_safe_path(path)
        return open(path, mode, encoding="utf-8")

    @classmethod
    def makedirs(cls, path):
        """
        Wrapped makedirs function that ensures that the path is within the cache directory
        """

        cls._ensure_safe_path(path)
        os.makedirs(path, exist_ok=True)

    @classmethod
    def exists(cls, path):
        """
        Wrapped exists function that ensures that the path is within the cache directory
        """

        cls._ensure_safe_path(path)
        return os.path.exists(path)

    @classmethod
    def is_within_cache(cls, path: str):
        """
        Check if a path is in the cache directory
        """
        return cls.is_within(path, cls._instance._cache_dir)

    @classmethod
    def match_template_cleanup(cls, root: str, name: str):
        template_validation_handler = TemplateValidationHandler()

        return (
            name.endswith(".yaml")
            and cls.is_within(
                root, f"{cls._instance._cache_dir}/{Settings.TEMPLATE_PREFIX_PATH}"
            )
            and not template_validation_handler.enforce_whitelist(name)
            and not template_validation_handler.enforce_blacklist(name)
        )

    @classmethod
    def match_image_cleanup(cls, root: str, name: str):
        """
        Check if a file is an image file that should be cleaned up
        """
        image_validation_handler = ImageValidationHandler()

        return name in Settings._DYN_IMG_EXT and (
            Filesystem.is_within(
                root,
                f"{Cache._instance._cache_dir}/{Settings.IMAGE_PREFIX_PATH}/icons",
            )
            or Filesystem.is_within(
                root,
                f"{Cache._instance._cache_dir}/{Settings.IMAGE_PREFIX_PATH}/backgrounds",
            )
            and not image_validation_handler.enforce_whitelist(name)
            and not image_validation_handler.enforce_blacklist(name)
        )

    @classmethod
    def cleanup_cache(cls, full: bool = False) -> None:
        """
        Clean all .yaml (template) files from the cache directory

        If full is True, also remove the .git directory and all other files
        """
        for root, dirs, files in os.walk(cls._instance._cache_dir, topdown=False):
            if f"{cls._instance._cache_dir}/.git" in root and not full:
                continue

            for name in files:
                if (
                    cls.match_template_cleanup(root, name)
                    or cls.match_image_cleanup(root, name)
                    or full
                ):
                    os.remove(os.path.join(root, name))

            for name in dirs:
                if name == ".git" and root == cls._instance._cache_dir and not full:
                    continue

                # Remove empty directories
                if not os.listdir(os.path.join(root, name)):
                    os.rmdir(os.path.join(root, name))

        if full and os.path.exists(cls._instance._cache_dir):
            os.rmdir(cls._instance._cache_dir)
            cls._instance._logger.info("Cache directory cleared")
