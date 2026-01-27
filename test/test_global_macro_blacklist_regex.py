import unittest
from os import getenv

from base_global_macro import BaseGlobalMacro

from zabbixci.settings import Settings

DEV_ZABBIX_URL = getenv("ZABBIX_URL")
DEV_ZABBIX_TOKEN = getenv("ZABBIX_TOKEN")
DEV_GIT_REMOTE = getenv("REMOTE")


class TestGlobalMacroBlacklistRegex(BaseGlobalMacro, unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        super().setUp()
        Settings.REGEX_MATCHING = True
        Settings.GLOBAL_MACRO_BLACKLIST = r"{\$NOT_EXISTING_.*}"

    # Test global macro deletion with regex blacklist checks
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

        Settings.GLOBAL_MACRO_BLACKLIST = r"{\$TEST_.*}"

        # Push changes to git
        changed = await self.zci.push()
        self.assertFalse(
            changed, "Global macro deletion detected inside of regex blacklist"
        )

        Settings.GLOBAL_MACRO_BLACKLIST = r"{\$NOT_EXISTING_.*}"


if __name__ == "__main__":
    unittest.main()
