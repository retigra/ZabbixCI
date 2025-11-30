import asyncio
from os import getenv

from base_test import BaseTest

from zabbixci import ZabbixCI
from zabbixci.cache.cleanup import Cleanup

DEV_ZABBIX_URL = getenv("ZABBIX_URL")
DEV_ZABBIX_TOKEN = getenv("ZABBIX_TOKEN")
DEV_GIT_REMOTE = getenv("REMOTE")
CACHE_PATH = getenv("CACHE_PATH")


class BaseScripts(BaseTest):
    def setUp(self):
        self.prep()

        self.settings.ZABBIX_URL = DEV_ZABBIX_URL
        self.settings.ZABBIX_TOKEN = DEV_ZABBIX_TOKEN
        self.settings.REMOTE = DEV_GIT_REMOTE
        self.settings.SKIP_VERSION_CHECK = True
        self.settings.REGEX_MATCHING = False
        self.settings.SET_VERSION = True

        self.settings.SYNC_TEMPLATES = False
        self.settings.SYNC_ICONS = False
        self.settings.SYNC_BACKGROUNDS = False
        self.settings.SYNC_ICON_MAPS = False
        self.settings.SYNC_SCRIPTS = True

        self.settings.SCRIPT_WHITELIST = ""
        self.settings.SCRIPT_BLACKLIST = ""

        self.zci = ZabbixCI(self.settings)

    async def restore_state(self):
        self.zci._git.force_push(
            ["+refs/remotes/origin/test:refs/heads/main"],
            self.settings.REMOTE,
        )

        Cleanup.cleanup_cache(self.settings, full=True)
        self.zci.create_git()

        whitelist = self.settings.SCRIPT_WHITELIST
        blacklist = self.settings.SCRIPT_BLACKLIST

        # Restore the state of Zabbix
        await self.zci.pull()

        self.settings.SCRIPT_WHITELIST = whitelist
        self.settings.SCRIPT_BLACKLIST = blacklist

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

        self.settings.PULL_BRANCH = "test"

        changed = await self.zci.pull()
        self.assertTrue(changed, "Template was not restored")

        self.settings.PULL_BRANCH = "main"
        changed = await self.zci.pull()
        self.assertTrue(changed, "Template deletion from Git was not detected")

    async def asyncTearDown(self):
        await self.zci._zabbix.zapi.logout()

        # Close custom session, if it exists
        if self.zci._zabbix._client_session:
            await self.zci._zabbix._client_session.close()

        # Wait a couple of cycles for the session to close
        await asyncio.sleep(0.25)
