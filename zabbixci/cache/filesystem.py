import logging
import os

logger = logging.getLogger(__name__)


class Filesystem:
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
                logger.debug(f"Found file: {os.path.join(root, name)}")

        return found_files

    @classmethod
    def real_path(cls, path: str):
        return os.path.realpath(path)

    @classmethod
    def is_within(cls, child: str, parent: str):
        """
        Check if a path is within another path
        """
        real_path = os.path.realpath(parent)
        return os.path.commonpath([real_path, os.path.realpath(child)]) == real_path
