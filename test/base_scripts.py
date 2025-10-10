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
CACHE_PATH = getenv("CACHE_PATH")


class BaseScripts:
    def setUp(self):
        Settings.CACHE_PATH = CACHE_PATH
        self.cache = Cache(Settings.CACHE_PATH)

        if os.path.exists(Settings.CACHE_PATH):
            Cleanup.cleanup_cache(full=True)

        logging.basicConfig(
            level=logging.WARNING,
            format="%(asctime)s - %(name)s - %(message)s",
        )

        Settings.ZABBIX_URL = DEV_ZABBIX_URL
        Settings.ZABBIX_TOKEN = DEV_ZABBIX_TOKEN
        Settings.REMOTE = DEV_GIT_REMOTE
        Settings.SKIP_VERSION_CHECK = True
        Settings.REGEX_MATCHING = False
        Settings.SET_VERSION = True

        Settings.SYNC_TEMPLATES = False
        Settings.SYNC_ICONS = False
        Settings.SYNC_BACKGROUNDS = False
        Settings.SYNC_ICON_MAPS = False
        Settings.SYNC_SCRIPTS = True

        Settings.SCRIPT_WHITELIST = ""
        Settings.SCRIPT_BLACKLIST = ""

        self.zci = ZabbixCI()

    async def restore_state(self):
        self.zci._git.force_push(
            ["+refs/remotes/origin/test:refs/heads/main"],
            Settings.REMOTE,
        )

        Cleanup.cleanup_cache(full=True)
        self.zci.create_git()

        whitelist = Settings.SCRIPT_WHITELIST
        blacklist = Settings.SCRIPT_BLACKLIST

        # Restore the state of Zabbix
        await self.zci.pull()

        Settings.SCRIPT_WHITELIST = whitelist
        Settings.SCRIPT_BLACKLIST = blacklist

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

    async def test_script_change(self):
        # Rename a script
        script = self.zci._zabbix.get_scripts(["Detect operating system"])[0]
        self.zci._zabbix.update_script({**script, "description": "Hello world"})

        # Push changes to git
        changed = await self.zci.push()
        self.assertTrue(changed, "Script change not detected")

        # Revert changes in Zabbix
        self.zci._zabbix.update_script({**script, "description": ""})
        # Restore to Git version
        changed = await self.zci.pull()
        self.assertTrue(changed, "Script was not restored")

        # Assert Git version is imported back into Zabbix
        matches = self.zci._zabbix.get_scripts(["Detect operating system"])
        self.assertEqual(len(matches), 1, "Script not found")

    async def test_script_rename(self):
        # Rename a script
        script = self.zci._zabbix.get_scripts(["Detect operating system"])[0]

        self.zci._zabbix.update_script(
            {**script, "name": "Detect operating system (renamed)"}
        )

        # Push changes to git
        changed = await self.zci.push()
        self.assertTrue(changed, "Renaming not detected")

        # Make changes in Zabbix
        self.zci._zabbix.update_script({**script, "name": "Detect operating system"})

        # Restore to Git version
        changed = await self.zci.pull()
        self.assertTrue(changed, "Script was not restored")

        # Assert Git version is restored
        matches = self.zci._zabbix.get_scripts(["Detect operating system (renamed)"])
        self.assertEqual(len(matches), 1, "Script not found")

    async def test_script_delete(self):
        # Delete a script
        script_id = self.zci._zabbix.get_scripts(["Traceroute"])[0]["scriptid"]
        self.zci._zabbix.delete_scripts([script_id])

        # Push changes to git
        changed = await self.zci.push()
        self.assertTrue(changed, "Deletion from Zabbix not detected")

        Settings.PULL_BRANCH = "test"

        changed = await self.zci.pull()
        self.assertTrue(changed, "Template was not restored")

        Settings.PULL_BRANCH = "main"
        changed = await self.zci.pull()
        self.assertTrue(changed, "Template deletion from Git was not detected")

    async def asyncTearDown(self):
        await self.zci._zabbix.zapi.logout()

        # Close custom session, if it exists
        if self.zci._zabbix._client_session:
            await self.zci._zabbix._client_session.close()

        # Wait a couple of cycles for the session to close
        await asyncio.sleep(0.25)
