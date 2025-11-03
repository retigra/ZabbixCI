import asyncio
from os import getenv

from base_test import BaseTest

from zabbixci import ZabbixCI
from zabbixci.cache.cleanup import Cleanup

DEV_ZABBIX_URL = getenv("ZABBIX_URL")
DEV_ZABBIX_TOKEN = getenv("ZABBIX_TOKEN")
DEV_GIT_REMOTE = getenv("REMOTE")
CACHE_PATH = getenv("CACHE_PATH")


class BaseImages(BaseTest):
    def setUp(self):
        self.prep()

        self.settings.ZABBIX_URL = DEV_ZABBIX_URL
        self.settings.ZABBIX_TOKEN = DEV_ZABBIX_TOKEN
        self.settings.REMOTE = DEV_GIT_REMOTE
        self.settings.REGEX_MATCHING = False
        self.settings.SKIP_VERSION_CHECK = True
        self.settings.SET_VERSION = True

        self.settings.SYNC_TEMPLATES = False
        self.settings.SYNC_ICONS = True
        self.settings.SYNC_BACKGROUNDS = True
        self.settings.SYNC_ICON_MAPS = False
        self.settings.SYNC_SCRIPTS = False

        self.settings.IMAGE_BLACKLIST = ""
        self.settings.IMAGE_WHITELIST = ""

        self.zci = ZabbixCI(self.settings)

    async def restore_state(self):
        self.zci._git.force_push(
            ["+refs/remotes/origin/test:refs/heads/main"],
            self.settings.REMOTE,
        )

        Cleanup.cleanup_cache(self.settings, full=True)
        self.zci.create_git()

        whitelist = self.settings.IMAGE_WHITELIST
        blacklist = self.settings.IMAGE_BLACKLIST

        self.settings.IMAGE_WHITELIST = ""
        self.settings.IMAGE_BLACKLIST = ""

        # Restore the state of Zabbix
        await self.zci.pull()

        self.settings.IMAGE_WHITELIST = whitelist
        self.settings.IMAGE_BLACKLIST = blacklist

    async def asyncSetUp(self):
        self.zci.create_git()
        await self.zci.create_zabbix()
        await self.restore_state()

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

        self.settings.PULL_BRANCH = "test"

        changed = await self.zci.pull()
        self.assertTrue(changed, "Image was not restored")

        self.settings.PULL_BRANCH = "main"
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
