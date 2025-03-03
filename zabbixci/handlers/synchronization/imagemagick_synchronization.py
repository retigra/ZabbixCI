import logging
from typing import Any

from zabbixci.cache.cache import Cache

logger = logging.getLogger(__name__)


class ImagemagickHandler:
    """
    Wand / ImageMagick wrapper for ZabbixCI, coverts images (icons) to different sizes and formats.
    """

    @classmethod
    def _convert(cls, image: Any, size: int, format: str) -> Any:
        """
        Convert an image to a different size and format

        :param image: Image to convert
        :param size: Size to convert to
        :param format: Format to convert to
        :return: Converted image
        """
        # Calculate scale factor by width
        width, height = image.size
        scale = size / width

        image.format = format

        # Resize image
        image.resize(width=size, height=int(height * scale))

        return image

    @classmethod
    def create_sized(
        cls,
        image_path: str,
        destination: str,
        base_name: str,
        file_type: str,
        sizes: list[int],
    ):
        """
        Create sized images based on the sizes in the settings

        :param image_path: Path to the image
        """
        from wand.image import Image  # type: ignore

        files: list[str] = []

        if not Cache.is_within_cache(image_path):
            logger.error(f"Image {image_path} is not within the cache")
            return files

        with Image(filename=image_path) as image:

            for size in sizes:
                file_name = f"{base_name}_({size}).png"

                converted_image = cls._convert(image.clone(), size, "png")
                converted_image.save(filename=f"{destination}/{file_name}")

                logger.info(f"Created: {file_name}")
                files.append(f"{destination}/{file_name}")

        return files
