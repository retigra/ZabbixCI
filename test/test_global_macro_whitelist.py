import unittest
from os import getenv

from base_global_macro import BaseGlobalMacro

from zabbixci.settings import Settings

DEV_ZABBIX_URL = getenv("ZABBIX_URL")
DEV_ZABBIX_TOKEN = getenv("ZABBIX_TOKEN")
DEV_GIT_REMOTE = getenv("REMOTE")


class TestGlobalMacroWhitelist(BaseGlobalMacro, unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        super().setUp()
        Settings.GLOBAL_MACRO_WHITELIST = "{$TEST_MACRO},{$ANOTHER_MACRO}"

    # Test global macro deletion with whitelist checks
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

        Settings.GLOBAL_MACRO_WHITELIST = "{$NONEXISTENT_MACRO}"

        # Push changes to git
        changed = await self.zci.push()
        self.assertFalse(changed, "Global macro deletion detected outside of whitelist")

        Settings.GLOBAL_MACRO_WHITELIST = "{$TEST_MACRO},{$ANOTHER_MACRO}"
        Settings.SYNC_GLOBAL_MACROS = False
        changed = await self.zci.push()
        self.assertFalse(
            changed, "Global macro deletion detected when sync is disabled"
        )

        Settings.SYNC_GLOBAL_MACROS = True


if __name__ == "__main__":
    unittest.main()
