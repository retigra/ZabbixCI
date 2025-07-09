import logging
from base64 import b64decode, b64encode

import regex

from zabbixci.assets.asset import Asset
from zabbixci.cache.cache import Cache
from zabbixci.settings import Settings

logger = logging.getLogger(__name__)


class Image(Asset):
    image_id: int | None = None
    image: bytes
    name: str
    type: str

    def __init__(
        self, base64: str, name: str, type: str = "icon", image_id: int | None = None
    ):
        self.image = b64decode(base64)
        self.name = name
        self.type = type
        self.image_id = image_id

    def __str__(self):
        return f"{self.name} ({self.type})"

    @property
    def _type_folder(self):
        return "icons" if self.type == "icon" else "backgrounds"

    def save(self):
        name_folders = self.name.split("/")[0:-1]

        Cache.makedirs(
            f"{Settings.CACHE_PATH}/{Settings.IMAGE_PREFIX_PATH}/{self._type_folder}/{'/'.join(name_folders)}",
        )

        with Cache.open(
            f"{Settings.CACHE_PATH}/{Settings.IMAGE_PREFIX_PATH}/{self._type_folder}/{self.name}.png",
            "wb",
        ) as file:
            file.write(self.image)

    def load(self, path: str):
        with Cache.open(f"{Settings.CACHE_PATH}/{path}/{self.name}.png", "rb") as file:
            self.image = file.read()

    def as_zabbix_dict(self):
        return {
            "image": b64encode(self.image).decode(),
            "name": self.name,
            "imagetype": "1" if self.type == "icon" else "2",
        }

    def minify(self):
        return Image("", self.name, self.type, self.image_id)

    @classmethod
    def from_zabbix(cls, image: dict):
        """
        Create an Image object from a Zabbix API image object

        See: https://www.zabbix.com/documentation/7.0/en/manual/api/reference/image/object
        """
        return cls(
            image["image"],
            image["name"],
            "icon" if image["imagetype"] == "1" else "background",
            image["imageid"],
        )

    @classmethod
    def open(cls, path: str):
        with Cache.open(path, "rb") as file:
            # TODO: Validation of path ending with /
            matches = regex.match(
                f".*{Settings.IMAGE_PREFIX_PATH}/(icons|backgrounds)/(.*).png", path
            )

            if not matches:
                logger.debug("Skipping invalid image path: %s", path)
                return None

            type = "icon" if matches[1] == "icons" else "background"
            return cls(b64encode(file.read()).decode(), matches[2], type)
