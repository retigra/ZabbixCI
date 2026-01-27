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


class BaseGlobalMacro:
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
        Settings.SYNC_ICONS = False
        Settings.SYNC_BACKGROUNDS = False
        Settings.SYNC_ICON_MAPS = False
        Settings.SYNC_GLOBAL_MACROS = True

        Settings.GLOBAL_MACRO_BLACKLIST = ""
        Settings.GLOBAL_MACRO_WHITELIST = ""

        self.zci = ZabbixCI()

    async def restore_state(self):
        self.zci._git.force_push(
            ["+refs/remotes/origin/test:refs/heads/main"],
            Settings.REMOTE,
        )

        Cleanup.cleanup_cache(full=True)
        self.zci.create_git()

        whitelist = Settings.GLOBAL_MACRO_WHITELIST
        blacklist = Settings.GLOBAL_MACRO_BLACKLIST

        Settings.GLOBAL_MACRO_WHITELIST = ""
        Settings.GLOBAL_MACRO_BLACKLIST = ""

        # Restore the state of Zabbix
        await self.zci.pull()

        Settings.GLOBAL_MACRO_WHITELIST = whitelist
        Settings.GLOBAL_MACRO_BLACKLIST = blacklist

    async def asyncSetUp(self):
        self.zci.create_git()
        await self.zci.create_zabbix()
        await self.restore_state()

    async def test_push_pull_remote_defaults(self):
        # Push default Zabbix global macros to remote
        await self.zci.push()

        # No changed when we have just pushed
        changed = await self.zci.pull()
        self.assertFalse(changed)

    async def test_global_macro_delete(self):
        # Get a global macro
        macros = self.zci._zabbix.get_global_macros(["{$TEST_MACRO}"])
        if not macros:
            # Create a test macro if it doesn't exist
            self.zci._zabbix.create_global_macro(
                {
                    "macro": "{$TEST_MACRO}",
                    "value": "test_value",
                    "description": "Test macro",
                }
            )
            macros = self.zci._zabbix.get_global_macros(["{$TEST_MACRO}"])

        macro_id = macros[0]["globalmacroid"]
        self.zci._zabbix.delete_global_macros([macro_id])

        # Push changes to git
        changed = await self.zci.push()
        self.assertTrue(changed, "Global macro deletion from Zabbix not detected")

        Settings.PULL_BRANCH = "test"

        changed = await self.zci.pull()
        self.assertTrue(changed, "Global macro was not restored")

        Settings.PULL_BRANCH = "main"
        changed = await self.zci.pull()
        self.assertTrue(changed, "Global macro deletion from Git was not detected")

    async def test_global_macro_change(self):
        # Get a global macro
        macros = self.zci._zabbix.get_global_macros(["{$TEST_MACRO}"])
        if not macros:
            # Create a test macro if it doesn't exist
            self.zci._zabbix.create_global_macro(
                {
                    "macro": "{$TEST_MACRO}",
                    "value": "test_value",
                    "description": "Test macro",
                }
            )
            macros = self.zci._zabbix.get_global_macros(["{$TEST_MACRO}"])

        macro = macros[0]
        original_value = macro["value"]

        # Update the macro
        self.zci._zabbix.update_global_macro(
            {"globalmacroid": macro["globalmacroid"], "value": "updated_value"}
        )

        # Push changes to git
        changed = await self.zci.push()
        self.assertTrue(changed, "Global macro change not detected")

        # Revert changes in Zabbix
        self.zci._zabbix.update_global_macro(
            {"globalmacroid": macro["globalmacroid"], "value": original_value}
        )

        # Restore to Git version
        changed = await self.zci.pull()
        self.assertTrue(changed, "Global macro was not restored")

        # Assert Git version is imported back into Zabbix
        matches = self.zci._zabbix.get_global_macros(["{$TEST_MACRO}"])
        self.assertEqual(len(matches), 1, "Global macro not found")
        self.assertEqual(matches[0]["value"], "updated_value", "Value not restored")

    async def asyncTearDown(self):
        await self.zci._zabbix.zapi.logout()

        # Close custom session, if it exists
        if self.zci._zabbix._client_session:
            await self.zci._zabbix._client_session.close()

        # Wait a couple of cycles for the session to close
        await asyncio.sleep(0.25)
