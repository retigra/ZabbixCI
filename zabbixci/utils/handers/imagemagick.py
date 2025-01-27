import logging

from zabbixci.settings import Settings
from zabbixci.utils.cache.cache import Cache

logger = logging.getLogger(__name__)


class Image:
    """
    Dummy wand image class
    """

    pass


class ImagemagickHandler:
    """
    Wand / ImageMagick wrapper for ZabbixCI, coverts images (icons) to different sizes and formats.
    """

    @classmethod
    def _convert(cls, image: Image, size: tuple[int, int], format: str) -> Image:
        """
        Convert an image to a different size and format

        :param image: Image to convert
        :param size: Size to convert to
        :param format: Format to convert to
        :return: Converted image
        """
        image.resize(size[0], size[1])
        image.format = format

        return image

    @classmethod
    def _get_sizes(cls):
        """
        Get the sizes to convert images to
        """
        return Settings.get_image_sizes()

    @classmethod
    def create_sized(cls, image_path: str, destination: str, base_name: str):
        """
        Create sized images based on the sizes in the settings

        :param image_path: Path to the image
        """
        from wand.image import Image

        files: list[str] = []
        with Cache.open(image_path, "rb") as file:
            image = Image(file=file)

            for size in cls._get_sizes():
                avg_size = int((size[0] + size[1]) / 2)
                file_name = f"{base_name}_({avg_size}).png"

                converted_image = cls._convert(image.clone(), size, "png")
                with Cache.open(f"{destination}/{file_name}", "wb") as file:
                    converted_image.save(file=file)

                logger.info(f"Created {file_name}")
                files.append(f"{destination}/{file_name}")

        return files
