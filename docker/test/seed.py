"""
Prepare a fresh Zabbix instance and git remote for the integration tests.

- Waits until the Zabbix API is available
- Creates an API token for the tests
- Removes all templates except the ones used by the tests
- Creates the image and icon map fixtures the tests expect
- Creates a local bare git remote with the resulting Zabbix state on the
  `main` and `test` branches (the tests restore `test` before every case)

The environment for the tests is written to stdout as KEY=value lines, logging
goes to stderr:

    uv run python docker/test/seed.py >> "$GITHUB_ENV"
"""

import argparse
import asyncio
import logging
import shutil
import struct
import sys
import tempfile
import time
import zlib
from base64 import b64encode
from os import path

import pygit2
from zabbix_utils import ZabbixAPI

from zabbixci import ZabbixCI
from zabbixci.cache.cache import Cache
from zabbixci.settings import Settings

logger = logging.getLogger("seed")

TOKEN_NAME = "zabbixci-tests"
IMAGE_NAME = "retigra_(200)"
ICON_MAP_NAME = "Cloud_Naming"

# Templates used by the tests, "Zabbix server health" is outside all whitelists
KEEP_TEMPLATES = [
    "Acronis Cyber Protect Cloud by HTTP",
    "Kubernetes API server by HTTP",
    "Kubernetes cluster state by HTTP",
    "Linux by Zabbix agent",
    "Windows by Zabbix agent",
    "Zabbix server health",
]


def png(width: int, height: int, rgb: tuple[int, int, int]) -> bytes:
    """
    Create a single color PNG image
    """

    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data))
        )

    row = b"\x00" + bytes(rgb) * width
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(row * height))
        + chunk(b"IEND", b"")
    )


def wait_for_api(url: str, user: str, password: str, timeout: int) -> ZabbixAPI:
    """
    Login to Zabbix, retrying until the frontend and database are ready
    """
    deadline = time.monotonic() + timeout

    while True:
        try:
            # Removing the default templates can take minutes
            api = ZabbixAPI(url=url, skip_version_check=True, timeout=600)
            api.login(user=user, password=password)
            logger.info("Connected to Zabbix %s at %s", api.version, url)
            return api
        except Exception as e:
            if time.monotonic() > deadline:
                raise TimeoutError(f"Zabbix API at {url} not available: {e}") from e

            logger.info("Waiting for Zabbix API: %s", e)
            time.sleep(5)


def create_token(api: ZabbixAPI, user: str) -> str:
    for token in api.token.get(filter={"name": TOKEN_NAME}):
        api.token.delete(token["tokenid"])

    userid = api.user.get(filter={"username": user})[0]["userid"]
    tokenid = api.token.create(name=TOKEN_NAME, userid=userid)["tokenids"][0]

    return api.token.generate(tokenid)[0]["token"]


def create_fixtures(api: ZabbixAPI):
    # Every push and pull parses all templates in the cache, keeping all
    # default templates would make the test suite take hours
    templates = api.template.get(output=["templateid", "host"])
    remove = [t["templateid"] for t in templates if t["host"] not in KEEP_TEMPLATES]

    if remove:
        api.template.delete(*remove)
        logger.info("Removed %s templates", len(remove))

    if not api.image.get(filter={"name": IMAGE_NAME}):
        api.image.create(
            name=IMAGE_NAME,
            imagetype=1,
            image=b64encode(png(200, 200, (0, 94, 184))).decode(),
        )
        logger.info("Created image %s", IMAGE_NAME)

    if not api.iconmap.get(filter={"name": ICON_MAP_NAME}):
        # Icons in use by an icon map can not be deleted, so these must not be
        # icons that the image tests delete
        icons = {
            image["name"]: image["imageid"]
            for image in api.image.get(
                output=["imageid", "name"],
                filter={"name": ["Cloud_(24)", "Cloud_(48)"]},
            )
        }

        api.iconmap.create(
            name=ICON_MAP_NAME,
            default_iconid=icons["Cloud_(24)"],
            mappings=[
                {
                    "inventory_link": 1,
                    "expression": "cloud",
                    "iconid": icons["Cloud_(48)"],
                }
            ],
        )
        logger.info("Created icon map %s", ICON_MAP_NAME)


def create_remote(remote: str):
    """
    Create an empty bare repository with an initial commit on main
    """
    if path.exists(remote):
        shutil.rmtree(remote)

    repository = pygit2.init_repository(remote, bare=True, initial_head="main")
    author = pygit2.Signature(Settings.GIT_AUTHOR_NAME, Settings.GIT_AUTHOR_EMAIL)
    tree = repository.TreeBuilder().write()
    repository.create_commit(
        "refs/heads/main", author, author, "Initial commit", tree, []
    )


async def push_state(url: str, token: str, remote: str):
    """
    Push the complete Zabbix state to main using ZabbixCI itself
    """
    Settings.ZABBIX_URL = url
    Settings.ZABBIX_TOKEN = token
    Settings.REMOTE = remote
    Settings.CACHE_PATH = path.join(tempfile.gettempdir(), "zabbixci-seed")
    Settings.SKIP_VERSION_CHECK = True
    Settings.SYNC_TEMPLATES = True
    Settings.SYNC_ICONS = True
    Settings.SYNC_BACKGROUNDS = True
    Settings.SYNC_ICON_MAPS = True

    # The cache is cloned from the remote, it must not exist yet
    shutil.rmtree(Settings.CACHE_PATH, ignore_errors=True)
    Cache(Settings.CACHE_PATH)

    zci = ZabbixCI()
    zci.create_git()
    await zci.create_zabbix()

    try:
        await zci.push()
    finally:
        await zci._zabbix.zapi.logout()
        shutil.rmtree(Settings.CACHE_PATH, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--zabbix-url", default="http://localhost:8080")
    parser.add_argument("--zabbix-user", default="Admin")
    parser.add_argument("--zabbix-password", default="zabbix")
    parser.add_argument(
        "--remote",
        default=path.join(tempfile.gettempdir(), "zabbixci-remote.git"),
        help="Path of the bare git repository to create, replaced if it exists",
    )
    parser.add_argument("--timeout", type=int, default=300)
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO, stream=sys.stderr, format="%(name)s - %(message)s"
    )

    api = wait_for_api(
        args.zabbix_url, args.zabbix_user, args.zabbix_password, args.timeout
    )
    token = create_token(api, args.zabbix_user)
    create_fixtures(api)
    api.logout()

    remote = path.abspath(args.remote)
    create_remote(remote)
    asyncio.run(push_state(args.zabbix_url, token, remote))

    repository = pygit2.Repository(remote)
    repository.branches.local.create("test", repository.revparse_single("main"))
    logger.info("Created git remote %s", remote)

    print(f"ZABBIX_URL={args.zabbix_url}")  # noqa: T201
    print(f"ZABBIX_TOKEN={token}")  # noqa: T201
    print(f"REMOTE={remote}")  # noqa: T201


if __name__ == "__main__":
    main()
