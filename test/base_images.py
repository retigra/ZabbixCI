import asyncio
import logging
import os
from os import getenv

from zabbixci import ZabbixCI
from zabbixci.cache.cache import Cache
from zabbixci.cache.cleanup import Cleanup
from zabbixci.settings import Settings

DEV_ZABBIX_URL = getenv("ZABBIX_URL")
DEV_ZABBIX_TOKEN = getenv("ZABBIX_TOKEN")
DEV_GIT_REMOTE = getenv("REMOTE")


class BaseImages:
    def setUp(self):
        Settings.CACHE_PATH = "/tmp/zabbixci"
        self.cache = Cache(Settings.CACHE_PATH)

        if os.path.exists(Settings.CACHE_PATH):
            Cleanup.cleanup_cache(full=True)

        logging.basicConfig(
            level=logging.ERROR,
            format="%(asctime)s - %(name)s - %(message)s",
        )

        Settings.ZABBIX_URL = DEV_ZABBIX_URL
        Settings.ZABBIX_TOKEN = DEV_ZABBIX_TOKEN
        Settings.REMOTE = DEV_GIT_REMOTE
        Settings.REGEX_MATCHING = False
        Settings.SET_VERSION = True

        Settings.SYNC_TEMPLATES = False
        Settings.SYNC_ICONS = True
        Settings.SYNC_BACKGROUNDS = True
        Settings.SYNC_ICON_MAPS = False

        Settings.IMAGE_BLACKLIST = ""
        Settings.IMAGE_WHITELIST = ""

        self.zci = ZabbixCI()

    async def restoreState(self):
        self.zci._git.force_push(
            ["+refs/remotes/origin/test:refs/heads/main"],
            Settings.REMOTE,
        )

        Cleanup.cleanup_cache(full=True)
        self.zci.create_git()

        whitelist = Settings.IMAGE_WHITELIST
        blacklist = Settings.IMAGE_BLACKLIST

        Settings.IMAGE_WHITELIST = ""
        Settings.IMAGE_BLACKLIST = ""

        # Restore the state of Zabbix
        await self.zci.pull()

        Settings.IMAGE_WHITELIST = whitelist
        Settings.IMAGE_BLACKLIST = blacklist

    async def asyncSetUp(self):
        self.zci.create_git()
        await self.zci.create_zabbix()
        await self.restoreState()

    async def test_push_pull_remote_defaults(self):
        # Push default Zabbix templates to remote
        await self.zci.push()

        # No changed when we have just pushed
        changed = await self.zci.pull()
        self.assertFalse(changed)

    async def test_image_delete(self):
        # Delete a template
        image_id = self.zci._zabbix.get_images(["Cloud_(128)"])[0]["imageid"]
        self.zci._zabbix.delete_images([image_id])

        # Push changes to git
        changed = await self.zci.push()
        self.assertTrue(changed, "Image deletion from Zabbix not detected")

        Settings.PULL_BRANCH = "test"

        changed = await self.zci.pull()
        self.assertTrue(changed, "Image was not restored")

        Settings.PULL_BRANCH = "main"
        changed = await self.zci.pull()
        self.assertTrue(changed, "Image deletion from Git was not detected")

    async def test_image_change(self):
        # Rename a template
        image = self.zci._zabbix.get_images(["Cloud_(128)"])[0]
        self.zci._zabbix.update_image(
            {"name": "Cloud_(128) (renamed)", "imageid": image["imageid"]}
        )

        # Push changes to git
        changed = await self.zci.push()
        self.assertTrue(changed, "Image change not detected")

        # Revert changes in Zabbix
        self.zci._zabbix.update_image(
            {"name": "Cloud_(128)", "imageid": image["imageid"]}
        )

        # Restore to Git version
        changed = await self.zci.pull()
        self.assertTrue(changed, "Image was not restored")

        # Assert Git version is imported back into Zabbix
        matches = self.zci._zabbix.get_images(["Cloud_(128) (renamed)"])
        self.assertEqual(len(matches), 1, "Image not found")

    async def asyncTearDown(self):
        await self.zci._zabbix.zapi.logout()

        # Close custom session, if it exists
        if self.zci._zabbix._client_session:
            await self.zci._zabbix._client_session.close()

        # Wait a couple of cycles for the session to close
        await asyncio.sleep(0.25)
