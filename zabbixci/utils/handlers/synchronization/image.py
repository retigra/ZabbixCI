import logging

import regex

from zabbixci.settings import Settings
from zabbixci.utils.cache.cache import Cache
from zabbixci.utils.handlers.synchronization.imagemagick import ImagemagickHandler
from zabbixci.utils.handlers.validation.image_validation import ImageValidationHandler
from zabbixci.utils.services.image import Image
from zabbixci.utils.zabbix.zabbix import Zabbix

logger = logging.getLogger(__name__)


class ImageHandler(ImageValidationHandler):
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
        if not Settings.SYNC_ICONS and not Settings.SYNC_BACKGROUNDS:
            return []

        search = (
            self.get_whitelist()
            if not self._use_regex() and self.get_whitelist()
            else None
        )

        images = self._zabbix.get_images(search)

        logger.info(f"Found {len(images)} image(s) in Zabbix")

        for image in images:
            image_object = Image.from_zabbix(image)

            if not self.image_validation(image_object):
                continue

            image_object.save()

        return images

    def generate_images(self) -> list[str]:
        """
        Read images from dynamic dir and create different sizes for Zabbix.
        """
        if not Cache.exists(
            f"{Settings.CACHE_PATH}/{Settings.IMAGE_PREFIX_PATH}/dynamic"
        ):
            logger.info("No dynamic images found")
            return []

        file_paths = Cache.get_files(
            f"{Settings.CACHE_PATH}/{Settings.IMAGE_PREFIX_PATH}/dynamic"
        )

        changed_files = []
        full_cache_path = Cache.real_path(Settings.CACHE_PATH)

        for path in file_paths:
            # Skip non-png files in the dynamic directory
            if not self.is_image(path):
                logger.warning(f"Skipping non-png file {path}")
                continue

            match_groups = regex.match(
                rf"({full_cache_path}\/{Settings.IMAGE_PREFIX_PATH}\/dynamic\/?.*)/(.+)\.(\w+)",
                path,
            )

            if not match_groups:
                logger.warning(
                    f"Could not extract destination and file name from {path}"
                )
                continue

            destination = match_groups.group(1).replace("dynamic", "icons")
            file_name = match_groups.group(2)
            file_type = match_groups.group(3)

            if not file_name:
                logger.warning(f"Could not extract file name from {path}")
                continue

            Cache.makedirs(destination)

            created_paths = ImagemagickHandler.create_sized(
                path,
                destination,
                file_name,
                file_type,
            )

            changed_files.extend(created_paths)

        return changed_files

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

        if not Settings.SYNC_ICONS and not Settings.SYNC_BACKGROUNDS:
            return []

        for file in changed_files:
            if not self.read_validation(file):
                continue

            image = Image.open(file)

            if not self.image_validation(image):
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

        if not Settings.SYNC_ICONS and not Settings.SYNC_BACKGROUNDS:
            return []

        # Check if deleted files are images and if they are imported, if not add to deletion queue
        for file in deleted_files:
            if not self.read_validation(file):
                continue

            image = Image.open(file)

            if not image:
                logger.warning(f"Could not open to be deleted file {file}")
                continue

            if not self.image_validation(image):
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
