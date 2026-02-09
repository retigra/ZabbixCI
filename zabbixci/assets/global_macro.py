import logging
import re
from typing import TextIO

from ruamel.yaml import YAML

from zabbixci.assets.asset import Asset
from zabbixci.cache.cache import Cache
from zabbixci.settings import ApplicationSettings

logger = logging.getLogger(__name__)
yaml = YAML()

HIDDEN_VALUE = "HIDDEN_VALUE"
SECRET_TYPE = 1


def slugify(name: str) -> str:
    """
    Create a stable, filesystem-safe filename for a macro name.
    """
    clean = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_")
    return f"{clean}.yaml"


class GlobalMacro(Asset):
    global_macro_id: int | None = None
    name: str
    value: str
    description: str
    type: int

    def __init__(
        self,
        name: str,
        value: str,
        description: str = "",
        type: int = 0,
        global_macro_id: int | None = None,
    ):
        self.name = name
        self.value = value
        self.description = description
        self.type = int(type)
        self.global_macro_id = global_macro_id

    def __str__(self):
        return self.name

    def _yaml_dump(self, stream: TextIO):
        yaml.dump(self.export_dict, stream)

    @property
    def filename(self) -> str:
        return slugify(self.name)

    @property
    def is_secret(self) -> bool:
        return self.type == SECRET_TYPE or self.value == HIDDEN_VALUE

    def save(self, settings: ApplicationSettings):
        cache_path = f"{settings.CACHE_PATH}/{settings.GLOBAL_MACRO_PREFIX_PATH}/"

        Cache.makedirs(cache_path)

        with Cache.open(
            f"{cache_path}/{self.filename}",
            "w",
        ) as file:
            self._yaml_dump(file)

    def minify(self):
        return GlobalMacro(
            name=self.name,
            value="",
            description="",
            type=self.type,
            global_macro_id=self.global_macro_id,
        )

    @property
    def export_dict(self):
        value = HIDDEN_VALUE if self.type == SECRET_TYPE else self.value

        return {
            "name": self.name,
            "value": value,
            "description": self.description,
            "type": int(self.type),
        }

    @property
    def zabbix_update_dict(self):
        if not self.global_macro_id:
            raise ValueError("global_macro_id is required for update operations")

        return {
            "globalmacroid": str(self.global_macro_id),
            "value": self.value,
            "description": self.description,
            "type": int(self.type),
        }

    @property
    def zabbix_create_dict(self):
        return {
            "macro": self.name,
            "value": self.value,
            "description": self.description,
            "type": int(self.type),
        }

    @classmethod
    def from_zabbix(cls, macro: dict):
        """
        Create a GlobalMacro object from a Zabbix API macro object.
        """
        name = macro.get("macro") or macro.get("name")
        if not name:
            logger.debug("Skipping macro without a name: %s", macro)
            return None

        macro_type = macro.get("type", 0)
        if isinstance(macro_type, str) and macro_type.isdigit():
            macro_type = int(macro_type)

        value = macro.get("value", "")
        if macro_type == SECRET_TYPE:
            value = HIDDEN_VALUE

        return cls(
            name=name,
            value=value,
            description=macro.get("description", "") or "",
            type=int(macro_type),
            global_macro_id=int(macro["globalmacroid"])
            if macro.get("globalmacroid")
            else None,
        )

    @classmethod
    def open(cls, path: str):
        with Cache.open(path, "r") as file:
            data = yaml.load(file) or {}

        name = data.get("name")
        if not name:
            logger.debug("Skipping macro without name in %s", path)
            return None

        macro_type = data.get("type", 0)
        if isinstance(macro_type, str) and macro_type.isdigit():
            macro_type = int(macro_type)

        return cls(
            name=name,
            value=data.get("value", "") or "",
            description=data.get("description", "") or "",
            type=int(macro_type),
        )

    @classmethod
    def partial_open(cls, path: str):
        """
        Load only the identifying fields of a macro from disk.
        """
        macro = cls.open(path)
        if not macro:
            return None
        return macro.minify()
