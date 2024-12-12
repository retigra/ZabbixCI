import os

REMOTE = os.getenv("GIT_REMOTE")
PARENT_GROUP = os.getenv("PARENT_GROUP", "Templates")
CACHE_PATH = os.getenv("CACHE_PATH", "./cache")

PUSH_BRANCH = os.getenv("PUSH_BRANCH", "development")
PULL_BRANCH = os.getenv("PULL_BRANCH", "main")
