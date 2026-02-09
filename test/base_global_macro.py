import asyncio
from os import getenv

from base_test import BaseTest

from zabbixci import ZabbixCI
from zabbixci.cache.cleanup import Cleanup

DEV_ZABBIX_URL = getenv("ZABBIX_URL")
DEV_ZABBIX_TOKEN = getenv("ZABBIX_TOKEN")
DEV_GIT_REMOTE = getenv("REMOTE")
CACHE_PATH = getenv("CACHE_PATH")


class BaseGlobalMacro(BaseTest):
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
        self.settings.SYNC_SCRIPTS = False
        self.settings.SYNC_GLOBAL_MACROS = True

        self.settings.GLOBAL_MACRO_BLACKLIST = ""
        self.settings.GLOBAL_MACRO_WHITELIST = ""

        self.zci = ZabbixCI(self.settings)

    async def restore_state(self):
        self.zci._git.force_push(
            ["+refs/remotes/origin/test:refs/heads/main"],
            self.settings.REMOTE,
        )

        Cleanup.cleanup_cache(self.settings, full=True)
        self.zci.create_git()

        whitelist = self.settings.GLOBAL_MACRO_WHITELIST
        blacklist = self.settings.GLOBAL_MACRO_BLACKLIST

        self.settings.GLOBAL_MACRO_WHITELIST = ""
        self.settings.GLOBAL_MACRO_BLACKLIST = ""

        # Restore the state of Zabbix
        await self.zci.pull()

        self.settings.GLOBAL_MACRO_WHITELIST = whitelist
        self.settings.GLOBAL_MACRO_BLACKLIST = blacklist

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

        macro_id = macros[0]["globalmacroid"]
        self.zci._zabbix.delete_global_macros([macro_id])

        # Push changes to git
        changed = await self.zci.push()
        self.assertTrue(changed, "Global macro deletion from Zabbix not detected")

        self.settings.PULL_BRANCH = "test"

        changed = await self.zci.pull()
        self.assertTrue(changed, "Global macro was not restored")

        self.settings.PULL_BRANCH = "main"
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
