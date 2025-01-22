import os
from base64 import b64decode, b64encode

from zabbixci.settings import Settings


class Image:
    image: bytes
    name: str
    type: str

    def __init__(self, base64: str, name: str, type: str = "icon"):
        self.image = b64decode(base64)
        self.name = name
        self.type = type

    def __str__(self):
        return f"{self.name} ({self.type})"

    def save(self, path: str):
        os.makedirs(path, exist_ok=True)

        with open(f"{Settings.CACHE_PATH}/{path}/{self.name}.png", "wb") as file:
            file.write(self.image)

    def load(self, path: str):
        with open(f"{Settings.CACHE_PATH}/{path}/{self.name}.png", "rb") as file:
            self.image = file.read()

    def as_zabbix_dict(self):
        return {
            "image": b64encode(self.image).decode(),
            "name": self.name,
            "imagetype": "1" if self.type == "icon" else "2",
        }

    @classmethod
    def from_zabbix(cls, image: dict):
        """
        Create an Image object from a Zabbix API image object

        See: https://www.zabbix.com/documentation/7.0/en/manual/api/reference/image/object
        """
        return cls(image["image"], image["name"])

    @classmethod
    def open(cls, path: str):
        with open(f"{Settings.CACHE_PATH}/{path}", "rb") as file:
            filename = path.split("/")[-1].split(".")[0]
            return cls(b64encode(file.read()).decode(), filename)
