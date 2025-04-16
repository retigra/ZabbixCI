import logging
import os
import os.path
from typing import Self

from zabbixci.cache.filesystem import Filesystem


class Cache(Filesystem):
    _logger = None
    _instance: Self
    _cache_dir: str

    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, "_instance"):
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
    def get_files(cls, path: str) -> list[str]:
        """
        Wrapped get_files function that ensures that the path is within the cache directory
        """

        cls._ensure_safe_path(path)
        real_path = os.path.realpath(path)

        found_files = []

        for root, _dirs, files in os.walk(real_path):
            for name in files:
                found_files.append(os.path.join(root, name))

        return found_files

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
