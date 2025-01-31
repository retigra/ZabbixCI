import os

from ruamel.yaml import YAML

yaml = YAML()


class Settings:
    _DYN_IMG_EXT = ["png", "jpg", "jpeg", "gif", "bmp", "svg"]
    ZABBIX_URL = "http://localhost:8080"
    ZABBIX_USER = None
    ZABBIX_PASSWORD = None
    ZABBIX_TOKEN = None
    REMOTE = None
    ROOT_TEMPLATE_GROUP = "Templates"
    GIT_AUTHOR_NAME = "Zabbix CI"
    GIT_AUTHOR_EMAIL = "zabbixci@localhost"
    PULL_BRANCH = "main"
    PUSH_BRANCH = "main"
    TEMPLATE_PREFIX_PATH = "templates"
    IMAGE_PREFIX_PATH = "images"
    TEMPLATE_WHITELIST = ""
    TEMPLATE_BLACKLIST = ""
    CACHE_PATH = "./cache"
    BATCH_SIZE = 5
    IGNORE_TEMPLATE_VERSION = False
    INSECURE_SSL_VERIFY = False
    GIT_USERNAME = "git"
    GIT_PASSWORD = None
    GIT_PUBKEY = None
    GIT_PRIVKEY = None
    GIT_KEYPASSPHRASE = None
    CA_BUNDLE = None
    DRY_RUN = False
    VENDOR = None
    SET_VERSION = False
    SYNC_ICONS = False
    SYNC_BACKGROUNDS = False
    SYNC_TEMPLATES = True
    IMAGE_WHITELIST = ""
    IMAGE_BLACKLIST = ""
    ICON_SIZES = "24,48,64,128"
    BACKGROUND_SIZES = "480,720,1080"
    REGEX_MATCHING = False

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
    def get_ICON_SIZES(cls):
        size_strings = cls.ICON_SIZES.split(",") if cls.ICON_SIZES else []
        return [int(size) for size in size_strings]

    @classmethod
    def get_BACKGROUND_SIZES(cls):
        size_strings = cls.BACKGROUND_SIZES.split(",") if cls.BACKGROUND_SIZES else []
        return [int(size) for size in size_strings]

    @classmethod
    def from_env(cls):
        for key in cls.__dict__.keys():
            if key in os.environ:
                setattr(cls, key, os.environ[key])

    @classmethod
    def read_config(cls, path):
        with open(path, "r") as f:
            data = yaml.load(f)
            for key, value in data.items():
                setattr(cls, key.upper(), value)
