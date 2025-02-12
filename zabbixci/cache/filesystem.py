import logging
import os

logger = logging.getLogger(__name__)


class Filesystem:
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
