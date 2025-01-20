from base64 import b64decode, b64encode


class Image:
    image: bytes
    name: str
    type: str

    def __init__(self, base64: str, name: str, type: str = "icon"):
        self.image = b64decode(base64)
        self.name = name
        self.type = type

    def __str__(self):
        return b64encode(self.image).decode()

    def save(self, path: str):
        with open(f"{path}/{self.name}.png", "wb") as file:
            file.write(self.image)

    def load(self, path: str):
        with open(f"{path}/{self.name}.png", "rb") as file:
            self.image = file.read()

    @classmethod
    def from_zabbix(cls, image: dict):
        """
        Create an Image object from a Zabbix API image object

        See: https://www.zabbix.com/documentation/7.0/en/manual/api/reference/image/object
        """
        return cls(image["image"], image["name"])
