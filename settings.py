import os

GIT_AUTHOR_NAME = "Zabbix"
GIT_AUTHOR_EMAIL = "zabbix@example.com"

REMOTE = ""
PARENT_GROUP = "Templates"
CACHE_PATH = "./cache"

PUSH_BRANCH = "development"
PULL_BRANCH = "main"

GIT_PREFIX_PATH = ""

WHITELIST = []
BLACKLIST = []


def get_settings():
    global GIT_AUTHOR_NAME, GIT_AUTHOR_EMAIL, REMOTE, PARENT_GROUP, CACHE_PATH, PUSH_BRANCH, PULL_BRANCH, GIT_PREFIX_PATH, WHITELIST, BLACKLIST
    GIT_AUTHOR_NAME = os.getenv("GIT_AUTHOR_NAME", "Zabbix")
    GIT_AUTHOR_EMAIL = os.getenv("GIT_AUTHOR_EMAIL", "zabbix@example.com")

    REMOTE = os.getenv("GIT_REMOTE")
    PARENT_GROUP = os.getenv("PARENT_GROUP", "Templates")
    CACHE_PATH = os.getenv("CACHE_PATH", "./cache")

    PUSH_BRANCH = os.getenv("PUSH_BRANCH", "development")
    PULL_BRANCH = os.getenv("PULL_BRANCH", "main")

    GIT_PREFIX_PATH = os.getenv("GIT_PREFIX_PATH", "")

    WHITELIST_ENV = os.getenv("WHITELIST")
    BLACKLIST_ENV = os.getenv("BLACKLIST")

    WHITELIST = WHITELIST_ENV.split(",") if WHITELIST_ENV else []
    BLACKLIST = BLACKLIST_ENV.split(",") if BLACKLIST_ENV else []
