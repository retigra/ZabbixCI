import os
from copy import deepcopy
from typing import TYPE_CHECKING, ClassVar, Self

from ruamel.yaml import YAML

if TYPE_CHECKING:
    from _typeshed import FileDescriptorOrPath

yaml = YAML()


class ApplicationSettings:
    def __init__(self, settings: Self | None = None):
        if settings:
            for key, value in settings.__dict__.items():
                setattr(self, key, deepcopy(value))

    _DYN_IMG_EXT: ClassVar[list[str]] = ["png", "jpg", "jpeg", "gif", "bmp", "svg"]
    VERBOSE: bool | None = False
    DEBUG: bool | None = False
    DEBUG_ALL: bool | None = False
    ZABBIX_URL: str | None = "http://localhost:8080"
    ZABBIX_USER: str | None = None
    ZABBIX_PASSWORD: str | None = None
    ZABBIX_TOKEN: str | None = None
    REMOTE: str
    ROOT_TEMPLATE_GROUP: str = "Templates"
    GIT_AUTHOR_NAME: str = "ZabbixCI"
    GIT_AUTHOR_EMAIL: str = "zabbixci@localhost"
    GIT_COMMIT_MESSAGE: str | None = None
    PULL_BRANCH: str = "main"
    PUSH_BRANCH: str = "main"
    TEMPLATE_PREFIX_PATH: str = "templates"
    IMAGE_PREFIX_PATH: str = "images"
    ICON_MAP_PREFIX_PATH: str = "icon-maps"
    SCRIPT_PREFIX_PATH: str = "scripts"
    TEMPLATE_WHITELIST: str = ""
    TEMPLATE_BLACKLIST: str = ""
    CACHE_PATH: str = "./cache"
    BATCH_SIZE: int = 5
    IGNORE_TEMPLATE_VERSION: bool = False
    INSECURE_SSL_VERIFY: bool = False
    GIT_USERNAME: str = "git"
    GIT_PASSWORD: str | None = None
    GIT_PUBKEY: str | None = None
    GIT_PRIVKEY: str | None = None
    GIT_KEYPASSPHRASE: str | None = None
    CA_BUNDLE: str | None = None
    DRY_RUN: bool = False
    VENDOR: str | None = None
    SET_VERSION: bool = False
    SYNC_ICONS: bool = False
    SYNC_BACKGROUNDS: bool = False
    SYNC_TEMPLATES: bool = True
    SYNC_ICON_MAPS: bool = False
    SYNC_SCRIPTS: bool = False
    IMAGE_WHITELIST: str = ""
    IMAGE_BLACKLIST: str = ""
    ICON_SIZES: str = "24,48,64,128"
    BACKGROUND_SIZES: str = "480,720,1080"
    REGEX_MATCHING: bool = False
    ICON_MAP_WHITELIST: str = ""
    ICON_MAP_BLACKLIST: str = ""
    SCRIPT_WHITELIST: str = ""
    SCRIPT_BLACKLIST: str = ""
    SCRIPT_WITHOUT_USRGRP: bool = False
    SCRIPT_DEFAULT_USRGRP: str = "Zabbix administrators"
    ZABBIX_KWARGS: ClassVar[dict] = {}
    GIT_KWARGS: ClassVar[dict] = {}
    SKIP_VERSION_CHECK: bool = False
    CREATE_TEMPLATE_GROUPS: bool = True
    CREATE_ROLLBACK_BRANCH: bool = True
    PUSH_ROLLBACK_BRANCH: bool = False

    def get_template_whitelist(self):
        return self.TEMPLATE_WHITELIST.split(",") if self.TEMPLATE_WHITELIST else []

    def get_template_blacklist(self):
        return self.TEMPLATE_BLACKLIST.split(",") if self.TEMPLATE_BLACKLIST else []

    def get_image_whitelist(self):
        return self.IMAGE_WHITELIST.split(",") if self.IMAGE_WHITELIST else []

    def get_image_blacklist(self):
        return self.IMAGE_BLACKLIST.split(",") if self.IMAGE_BLACKLIST else []

    def get_icon_map_whitelist(self):
        return self.ICON_MAP_WHITELIST.split(",") if self.ICON_MAP_WHITELIST else []

    def get_icon_map_blacklist(self):
        return self.ICON_MAP_BLACKLIST.split(",") if self.ICON_MAP_BLACKLIST else []

    def get_script_whitelist(self):
        return self.SCRIPT_WHITELIST.split(",") if self.SCRIPT_WHITELIST else []

    def get_script_blacklist(self):
        return self.SCRIPT_BLACKLIST.split(",") if self.SCRIPT_BLACKLIST else []

    def get_icon_sizes(self):
        size_strings = self.ICON_SIZES.split(",") if self.ICON_SIZES else []
        return [int(size) for size in size_strings]

    def get_background_sizes(self):
        size_strings = self.BACKGROUND_SIZES.split(",") if self.BACKGROUND_SIZES else []
        return [int(size) for size in size_strings]


class ZabbixCISettings(ApplicationSettings):
    def from_env(self):
        for key, value in self.__dict__.items():
            # Dict values can only be set in the yaml config file
            if isinstance(value, dict):
                continue

            if key in os.environ:
                if isinstance(value, bool):
                    setattr(self, key, os.environ[key].lower() == "true")
                else:
                    setattr(self, key, os.environ[key])

    def read_config(self, file: "FileDescriptorOrPath"):
        with open(file, encoding="utf-8") as f:
            data = yaml.load(f)
            for key, value in data.items():
                setattr(self, key.upper(), value)


__all__ = ["ApplicationSettings", "ZabbixCISettings"]
