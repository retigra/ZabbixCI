from zabbixci.assets.asset import Asset
from typing import TextIO, TypedDict
from zabbixci.cache.cache import Cache
from ruamel.yaml import YAML
from os import path

from zabbixci.settings import Settings

yaml = YAML()


class ScriptParameter(TypedDict):
    name: str
    value: str


class Script(Asset):
    """
    Python representation of a Zabbix script https://www.zabbix.com/documentation/7.0/en/manual/api/reference/script/object#script.
    """

    scriptid: str
    name: str
    command: str
    host_access: str
    usrgrpid: str
    groupid: str
    description: str
    confirmation: str
    type: str
    execute_on: str
    timeout: str
    scope: str
    port: str
    authtype: str
    username: str
    password: str
    publickey: str
    privatekey: str
    menu_path: str
    url: str
    new_window: str
    manualinput: str
    manualinput_prompt: str
    manualinput_validator: str
    manualinput_validator_type: str
    manualinput_default_value: str
    parameters: list[ScriptParameter]

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

        self.parameters = [
            ScriptParameter(**param) for param in kwargs.get("parameters", [])
        ]

    @property
    def unique_name(self) -> str:
        if self.menu_path:
            return f"{self.menu_path}/{self.name}"
        return self.name

    @property
    def zabbix_dict(self) -> dict:
        return {
            "name": self.name,
            "command": self.command,
            "host_access": self.host_access,
            "usrgrpid": self.usrgrpid,
            "groupid": self.groupid,
            "description": self.description,
            "confirmation": self.confirmation,
            "type": self.type,
            "execute_on": self.execute_on,
            "timeout": self.timeout,
            "scope": self.scope,
            "port": self.port,
            "authtype": self.authtype,
            "username": self.username,
            "password": self.password,
            "publickey": self.publickey,
            "privatekey": self.privatekey,
            "menu_path": self.menu_path,
            "url": self.url,
            "new_window": self.new_window,
            "manualinput": self.manualinput,
            "manualinput_prompt": self.manualinput_prompt,
            "manualinput_validator": self.manualinput_validator,
            "manualinput_validator_type": self.manualinput_validator_type,
            "manualinput_default_value": self.manualinput_default_value,
            "parameters": self.parameters,
        }

    @classmethod
    def from_zabbix(cls, script: dict):
        """
        Construct Script object from Zabbix API response.
        """
        return cls(
            **script,
        )

    def _yaml_dump(self, stream: TextIO):
        """
        Dump Zabbix importable template to stream
        """
        script_export = self.__dict__.copy()

        del script_export["scriptid"]  # scriptid is not part of the export

        yaml.dump(script_export, stream)

    def save(self):
        # get folder structure to file
        folder = path.dirname(self.unique_name)

        Cache.makedirs(
            f"{Settings.CACHE_PATH}/{Settings.SCRIPT_PREFIX_PATH}/{folder}",
        )

        with Cache.open(
            f"{Settings.CACHE_PATH}/{Settings.SCRIPT_PREFIX_PATH}/{folder}/{self.name}.yaml",
            "w",
        ) as file:
            self._yaml_dump(file)

    @staticmethod
    def open(path: str):
        """
        Open a template from the cache
        """
        with Cache.open(path, "r") as file:
            return Script(**yaml.load(file))
