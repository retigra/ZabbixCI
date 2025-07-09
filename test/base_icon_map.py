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


class BaseIconMap:
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
        Settings.SKIP_VERSION_CHECK = True
        Settings.SET_VERSION = True

        Settings.SYNC_TEMPLATES = False
        Settings.SYNC_ICONS = True
        Settings.SYNC_BACKGROUNDS = False
        Settings.SYNC_ICON_MAPS = True

        Settings.ICON_MAP_BLACKLIST = ""
        Settings.ICON_MAP_WHITELIST = ""

        self.zci = ZabbixCI()

    async def restore_state(self):
        self.zci._git.force_push(
            ["+refs/remotes/origin/test:refs/heads/main"],
            Settings.REMOTE,
        )

        Cleanup.cleanup_cache(full=True)
        self.zci.create_git()

        whitelist = Settings.ICON_MAP_WHITELIST
        blacklist = Settings.ICON_MAP_BLACKLIST

        Settings.ICON_MAP_WHITELIST = ""
        Settings.ICON_MAP_BLACKLIST = ""

        # Restore the state of Zabbix
        await self.zci.pull()

        Settings.ICON_MAP_WHITELIST = whitelist
        Settings.ICON_MAP_BLACKLIST = blacklist

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

    async def test_icon_map_delete(self):
        # Delete a template
        icon_map_id = self.zci._zabbix.get_icon_maps(["Cloud_Naming"])[0]["iconmapid"]
        self.zci._zabbix.delete_icon_maps([icon_map_id])

        # Push changes to git
        changed = await self.zci.push()
        self.assertTrue(changed, "Icon map deletion from Zabbix not detected")

        Settings.PULL_BRANCH = "test"

        changed = await self.zci.pull()
        self.assertTrue(changed, "Icon map was not restored")

        Settings.PULL_BRANCH = "main"
        changed = await self.zci.pull()
        self.assertTrue(changed, "Icon map deletion from Git was not detected")

    async def test_icon_map_change(self):
        # Rename a template
        image = self.zci._zabbix.get_icon_maps(["Cloud_Naming"])[0]
        self.zci._zabbix.update_icon_map(
            {"name": "Cloud_Naming_(renamed)", "iconmapid": image["iconmapid"]}
        )

        # Push changes to git
        changed = await self.zci.push()
        self.assertTrue(changed, "Icon map change not detected")

        # Revert changes in Zabbix
        self.zci._zabbix.update_icon_map(
            {"name": "Cloud_Naming", "iconmapid": image["iconmapid"]}
        )

        # Restore to Git version
        changed = await self.zci.pull()
        self.assertTrue(changed, "Icon map was not restored")

        # Assert Git version is imported back into Zabbix
        matches = self.zci._zabbix.get_icon_maps(["Cloud_Naming_(renamed)"])
        self.assertEqual(len(matches), 1, "Icon map not found")

    async def asyncTearDown(self):
        await self.zci._zabbix.zapi.logout()

        # Close custom session, if it exists
        if self.zci._zabbix._client_session:
            await self.zci._zabbix._client_session.close()

        # Wait a couple of cycles for the session to close
        await asyncio.sleep(0.25)
