import os
from ruamel.yaml import YAML

yaml = YAML()


class Settings:
    ZABBIX_URL = "http://localhost:8080"
    ZABBIX_USER = None
    ZABBIX_PASSWORD = None
    ZABBIX_TOKEN = None
    REMOTE = None
    PARENT_GROUP = "Templates"
    GIT_AUTHOR_NAME = "Zabbix CI"
    GIT_AUTHOR_EMAIL = "zabbixci@localhost"
    PULL_BRANCH = "main"
    PUSH_BRANCH = "main"
    GIT_PREFIX_PATH = ""
    WHITELIST = []
    BLACKLIST = []
    CACHE_PATH = "./cache"

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
