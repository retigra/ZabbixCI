import logging
import os

from zabbixci.settings import Settings
from zabbixci.utils.services.image import Image
from zabbixci.utils.zabbix.zabbix import Zabbix

logger = logging.getLogger(__name__)


class ImageHandler:
    """
    Handler for importing images into Zabbix based on changed files. Includes validation steps based on settings.

    :param zabbix: Zabbix instance
    """

    _zabbix: Zabbix

    def __init__(self, zabbix: Zabbix):
        self._zabbix = zabbix

    def images_to_cache(self) -> list[str]:
        """
        Export Zabbix images to the cache
        """
        images = self._zabbix.get_images()

        logger.info(f"Found {len(images)} images in Zabbix")

        for image in images:
            image_object = Image.from_zabbix(image)
            image_object.save()

        return images

    def _read_validation(self, changed_file: str) -> bool:
        """
        Validation steps to perform on a changed file before it is processed as a image
        """
        if not changed_file.endswith(".png"):
            return False

        # Check if file is within the desired path
        if not changed_file.startswith(Settings.IMAGE_PREFIX_PATH):
            logger.debug(f"Skipping .png file {changed_file} outside of prefix path")
            return False

        return True

    def _image_validation(self, image: Image | None) -> bool:
        if not image:
            return False

        return True

    def import_file_changes(
        self, changed_files: list[str], image_objects: list[dict]
    ) -> list[str]:
        """
        Import images into Zabbix based on changed files.
        Changes are parsed and validated before importing.

        :param changed_files: List of changed files
        :param image_objects: List of image objects from Zabbix, needed for choice between creation or update

        :return: List of imported image UUIDs
        """
        images: list[Image] = []

        for file in changed_files:
            if not self._read_validation(file):
                continue

            image = Image.open(file)

            if not self._image_validation(image):
                continue

            images.append(image)
            logger.info(f"Detected change in image: {image.name}")

        # Group images by level
        failed_images: list[Image] = []

        def __import_image(image: Image):
            if image.name in [t["name"] for t in image_objects]:
                logger.info(f"Updating {image.name}")

                old_image = next(
                    filter(lambda dt: dt["name"] == image.name, image_objects)
                )

                return self._zabbix.update_image(
                    {
                        "imageid": old_image["imageid"],
                        "image": image.as_zabbix_dict()["image"],
                    }
                )
            else:
                logger.info(f"Creating {image.name}")
                return self._zabbix.create_image(image.as_zabbix_dict())

        # Import the images
        for image in images:
            if not Settings.DRY_RUN:
                try:
                    __import_image(image)
                except Exception as e:
                    logger.warning(
                        f"Error importing image {image.name}, will try to import later"
                    )
                    logger.debug(f"Error details: {e}")
                    failed_images.append(image)

        if len(failed_images):
            for image in failed_images:
                try:
                    __import_image(image)
                except Exception as e:
                    logger.error(f"Error importing image {image}: {e}")

        return [t.name for t in images]

    def delete_file_changes(
        self,
        deleted_files: list[str],
        imported_image_names: list[str],
        image_objects: list[dict],
    ):
        """
        Delete images from Zabbix based on deleted files.

        :param deleted_files: List of deleted files
        :param imported_image_names: List of imported image names
        :param image_objects: List of image objects from Zabbix needed for deletion in current Zabbix instance

        :return: List of deleted image names
        """
        deletion_queue: list[str] = []

        # Check if deleted files are images and if they are imported, if not add to deletion queue
        for file in deleted_files:
            if not self._read_validation(file):
                continue

            image = Image.open(file)

            if not image:
                logger.warning(f"Could not open to be deleted file {file}")
                continue

            if not self._image_validation(image):
                continue

            if image.name in imported_image_names:
                logger.debug(f"Image {image.name} was just imported, skipping deletion")
                continue

            deletion_queue.append(image.name)
            logger.info(f"Added {image.name} to deletion queue")

        # Delete images in deletion queue
        if len(deletion_queue):
            image_ids = [
                # Get image IDs from Zabbix
                t["imageid"]
                for t in list(
                    filter(lambda dt: dt["name"] in deletion_queue, image_objects)
                )
            ]

            logger.info(f"Deleting {len(image_ids)} images from Zabbix")

            if len(image_ids):
                if not Settings.DRY_RUN:
                    self._zabbix.delete_images(image_ids)

        return deletion_queue
