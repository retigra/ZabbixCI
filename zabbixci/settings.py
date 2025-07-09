import os

from ruamel.yaml import YAML

yaml = YAML()


class Settings:
    _DYN_IMG_EXT = ["png", "jpg", "jpeg", "gif", "bmp", "svg"]
    VERBOSE: bool | None = False
    DEBUG: bool | None = False
    DEBUG_ALL: bool | None = False
    ZABBIX_URL: str | None = "http://localhost:8080"
    ZABBIX_USER: str | None = None
    ZABBIX_PASSWORD: str | None = None
    ZABBIX_TOKEN: str | None = None
    REMOTE: str | None = None
    ROOT_TEMPLATE_GROUP: str = "Templates"
    GIT_AUTHOR_NAME: str = "ZabbixCI"
    GIT_AUTHOR_EMAIL: str = "zabbixci@localhost"
    GIT_COMMIT_MESSAGE: str | None = None
    PULL_BRANCH: str = "main"
    PUSH_BRANCH: str = "main"
    TEMPLATE_PREFIX_PATH: str = "templates"
    IMAGE_PREFIX_PATH: str = "images"
    ICON_MAP_PREFIX_PATH: str = "icon-maps"
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
    IMAGE_WHITELIST: str = ""
    IMAGE_BLACKLIST: str = ""
    ICON_SIZES: str = "24,48,64,128"
    BACKGROUND_SIZES: str = "480,720,1080"
    REGEX_MATCHING: bool = False
    ICON_MAP_WHITELIST: str = ""
    ICON_MAP_BLACKLIST: str = ""
    ZABBIX_KWARGS: dict = {}
    GIT_KWARGS: dict = {}
    SKIP_VERSION_CHECK: bool = False

    @classmethod
    def get_template_whitelist(cls):
        return cls.TEMPLATE_WHITELIST.split(",") if cls.TEMPLATE_WHITELIST else []

    @classmethod
    def get_template_blacklist(cls):
        return cls.TEMPLATE_BLACKLIST.split(",") if cls.TEMPLATE_BLACKLIST else []

    @classmethod
    def get_image_whitelist(cls):
        return cls.IMAGE_WHITELIST.split(",") if cls.IMAGE_WHITELIST else []

    @classmethod
    def get_image_blacklist(cls):
        return cls.IMAGE_BLACKLIST.split(",") if cls.IMAGE_BLACKLIST else []

    @classmethod
    def get_icon_map_whitelist(cls):
        return cls.ICON_MAP_WHITELIST.split(",") if cls.ICON_MAP_WHITELIST else []

    @classmethod
    def get_icon_map_blacklist(cls):
        return cls.ICON_MAP_BLACKLIST.split(",") if cls.ICON_MAP_BLACKLIST else []

    @classmethod
    def get_icon_sizes(cls):
        size_strings = cls.ICON_SIZES.split(",") if cls.ICON_SIZES else []
        return [int(size) for size in size_strings]

    @classmethod
    def get_background_sizes(cls):
        size_strings = cls.BACKGROUND_SIZES.split(",") if cls.BACKGROUND_SIZES else []
        return [int(size) for size in size_strings]

    @classmethod
    def from_env(cls):
        for key, value in cls.__dict__.items():
            # Dict values can only be set in the yaml config file
            if isinstance(value, dict):
                continue

            if key in os.environ:
                if isinstance(value, bool):
                    setattr(cls, key, os.environ[key].lower() == "true")
                else:
                    setattr(cls, key, os.environ[key])

    @classmethod
    def read_config(cls, path):
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.load(f)
            for key, value in data.items():
                setattr(cls, key.upper(), value)
