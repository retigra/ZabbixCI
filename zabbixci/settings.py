import os
from typing import TYPE_CHECKING

from ruamel.yaml import YAML

if TYPE_CHECKING:
    from _typeshed import FileDescriptorOrPath

yaml = YAML()


class ApplicationSettings:
    _DYN_IMG_EXT: list[str]
    VERBOSE: bool
    DEBUG: bool
    DEBUG_ALL: bool
    ZABBIX_URL: str
    ZABBIX_USER: str | None
    ZABBIX_PASSWORD: str | None
    ZABBIX_TOKEN: str | None
    REMOTE: str
    ROOT_TEMPLATE_GROUP: str
    GIT_AUTHOR_NAME: str
    GIT_AUTHOR_EMAIL: str
    GIT_COMMIT_MESSAGE: str | None
    PULL_BRANCH: str
    PUSH_BRANCH: str
    TEMPLATE_PREFIX_PATH: str
    IMAGE_PREFIX_PATH: str
    ICON_MAP_PREFIX_PATH: str
    SCRIPT_PREFIX_PATH: str
    TEMPLATE_WHITELIST: str
    TEMPLATE_BLACKLIST: str
    CACHE_PATH: str
    BATCH_SIZE: int
    IGNORE_TEMPLATE_VERSION: bool
    INSECURE_SSL_VERIFY: bool
    GIT_USERNAME: str
    GIT_PASSWORD: str | None
    GIT_PUBKEY: str | None
    GIT_PRIVKEY: str | None
    GIT_KEYPASSPHRASE: str | None
    CA_BUNDLE: str | None
    DRY_RUN: bool
    VENDOR: str | None
    SET_VERSION: bool
    SYNC_ICONS: bool
    SYNC_BACKGROUNDS: bool
    SYNC_TEMPLATES: bool
    SYNC_ICON_MAPS: bool
    SYNC_SCRIPTS: bool
    SYNC_GLOBAL_MACROS: bool = False
    IMAGE_WHITELIST: str
    IMAGE_BLACKLIST: str
    ICON_SIZES: str
    BACKGROUND_SIZES: str
    REGEX_MATCHING: bool
    ICON_MAP_WHITELIST: str
    ICON_MAP_BLACKLIST: str
    SCRIPT_WHITELIST: str
    SCRIPT_BLACKLIST: str
    GLOBAL_MACRO_WHITELIST: str = ""
    GLOBAL_MACRO_BLACKLIST: str = ""
    SCRIPT_WITHOUT_USRGRP: bool
    SCRIPT_DEFAULT_USRGRP: str
    ZABBIX_KWARGS: dict
    GIT_KWARGS: dict
    SKIP_VERSION_CHECK: bool
    CREATE_TEMPLATE_GROUPS: bool
    CREATE_ROLLBACK_BRANCH: bool
    PUSH_ROLLBACK_BRANCH: bool

    def __init__(self) -> None:
        # defaults moved from class-level assignments
        self._DYN_IMG_EXT = ["png", "jpg", "jpeg", "gif", "bmp", "svg"]
        self.VERBOSE = False
        self.DEBUG = False
        self.DEBUG_ALL = False
        self.ZABBIX_URL = "http://localhost:8080"
        self.ZABBIX_USER = None
        self.ZABBIX_PASSWORD = None
        self.ZABBIX_TOKEN = None
        self.REMOTE = ""
        self.ROOT_TEMPLATE_GROUP = "Templates"
        self.GIT_AUTHOR_NAME = "ZabbixCI"
        self.GIT_AUTHOR_EMAIL = "zabbixci@localhost"
        self.GIT_COMMIT_MESSAGE = None
        self.PULL_BRANCH = "main"
        self.PUSH_BRANCH = "main"
        self.TEMPLATE_PREFIX_PATH = "templates"
        self.IMAGE_PREFIX_PATH = "images"
        self.ICON_MAP_PREFIX_PATH = "icon-maps"
        self.SCRIPT_PREFIX_PATH = "scripts"
        self.GLOBAL_MACRO_PREFIX_PATH = "global-macros"
        self.TEMPLATE_WHITELIST = ""
        self.TEMPLATE_BLACKLIST = ""
        self.CACHE_PATH = "./cache"
        self.BATCH_SIZE = 5
        self.IGNORE_TEMPLATE_VERSION = False
        self.INSECURE_SSL_VERIFY = False
        self.GIT_USERNAME = "git"
        self.GIT_PASSWORD = None
        self.GIT_PUBKEY = None
        self.GIT_PRIVKEY = None
        self.GIT_KEYPASSPHRASE = None
        self.CA_BUNDLE = None
        self.DRY_RUN = False
        self.VENDOR = None
        self.SET_VERSION = False
        self.SYNC_ICONS = False
        self.SYNC_BACKGROUNDS = False
        self.SYNC_TEMPLATES = True
        self.SYNC_ICON_MAPS = False
        self.SYNC_SCRIPTS = False
        self.SYNC_GLOBAL_MACROS = False
        self.IMAGE_WHITELIST = ""
        self.IMAGE_BLACKLIST = ""
        self.ICON_SIZES = "24,48,64,128"
        self.BACKGROUND_SIZES = "480,720,1080"
        self.REGEX_MATCHING = False
        self.ICON_MAP_WHITELIST = ""
        self.ICON_MAP_BLACKLIST = ""
        self.SCRIPT_WHITELIST = ""
        self.SCRIPT_BLACKLIST = ""
        self.GLOBAL_MACRO_WHITELIST = ""
        self.GLOBAL_MACRO_BLACKLIST = ""
        self.SCRIPT_WITHOUT_USRGRP = False
        self.SCRIPT_DEFAULT_USRGRP = "Zabbix administrators"
        self.ZABBIX_KWARGS = {}
        self.GIT_KWARGS = {}
        self.SKIP_VERSION_CHECK = False
        self.CREATE_TEMPLATE_GROUPS = True
        self.CREATE_ROLLBACK_BRANCH = True
        self.PUSH_ROLLBACK_BRANCH = False

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

    @classmethod
    def get_global_macro_whitelist(cls):
        return (
            cls.GLOBAL_MACRO_WHITELIST.split(",") if cls.GLOBAL_MACRO_WHITELIST else []
        )

    @classmethod
    def get_global_macro_blacklist(cls):
        return (
            cls.GLOBAL_MACRO_BLACKLIST.split(",") if cls.GLOBAL_MACRO_BLACKLIST else []
        )

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
                elif isinstance(value, int):
                    setattr(self, key, int(os.environ[key]))
                else:
                    setattr(self, key, os.environ[key])

    def read_config(self, file: "FileDescriptorOrPath"):
        with open(file, encoding="utf-8") as f:
            data = yaml.load(f)
            for key, value in data.items():
                setattr(self, key.upper(), value)


__all__ = ["ApplicationSettings", "ZabbixCISettings"]
