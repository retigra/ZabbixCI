import os

GIT_AUTHOR_NAME = os.getenv("GIT_AUTHOR_NAME", "Zabbix")
GIT_AUTHOR_EMAIL = os.getenv("GIT_AUTHOR_EMAIL", "zabbix@example.com")

REMOTE = os.getenv("GIT_REMOTE")
PARENT_GROUP = os.getenv("PARENT_GROUP", "Templates")
CACHE_PATH = os.getenv("CACHE_PATH", "./cache")

PUSH_BRANCH = os.getenv("PUSH_BRANCH", "development")
PULL_BRANCH = os.getenv("PULL_BRANCH", "main")

GIT_PREFIX_PATH = os.getenv("GIT_PREFIX_PATH", "")

WHITELIST = os.getenv("WHITELIST", "").split(";")
BLACKLIST = os.getenv("BLACKLIST", "").split(";")
