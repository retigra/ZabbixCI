import unittest
from os import getenv

from base_scripts import BaseScripts

DEV_ZABBIX_URL = getenv("ZABBIX_URL")
DEV_ZABBIX_TOKEN = getenv("ZABBIX_TOKEN")
DEV_GIT_REMOTE = getenv("REMOTE")


class TestScriptsWhitelistRegex(BaseScripts, unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        super().setUp()
        self.settings.REGEX_MATCHING = True
        self.settings.SCRIPT_WHITELIST = "(Traceroute|Detect operating system).*"

    # Test script deletion with whitelist checks
    async def test_script_delete(self):
        # Delete a script
        script_id = self.zci._zabbix.get_scripts(["Traceroute"])[0]["scriptid"]
        self.zci._zabbix.delete_scripts([script_id])

        self.settings.SCRIPT_WHITELIST = "Trace"  # Should not match partial names

        # Push changes to git
        changed = await self.zci.push()
        self.assertFalse(changed, "Script deletion detected outside of whitelist")

        self.settings.SCRIPT_WHITELIST = "Trace"  # Should not match partial names

        # Push changes to git
        changed = await self.zci.push()
        self.assertFalse(changed, "Script deletion detected outside of whitelist")


if __name__ == "__main__":
    unittest.main()
