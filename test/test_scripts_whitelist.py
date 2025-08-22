import unittest
from os import getenv

from base_scripts import BaseScripts

from zabbixci.settings import Settings

DEV_ZABBIX_URL = getenv("ZABBIX_URL")
DEV_ZABBIX_TOKEN = getenv("ZABBIX_TOKEN")
DEV_GIT_REMOTE = getenv("REMOTE")


class TestScriptsWhitelist(BaseScripts, unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        super().setUp()
        Settings.SCRIPT_WHITELIST = (
            "Traceroute,Ping,Detect operating system,Detect operating system (renamed)"
        )

    # Test script deletion with whitelist checks
    async def test_script_delete(self):
        # Delete a script
        script_id = self.zci._zabbix.get_scripts(["Traceroute"])[0]["scriptid"]
        self.zci._zabbix.delete_scripts([script_id])

        Settings.SCRIPT_WHITELIST = "Nonexistent script"

        # Push changes to git
        changed = await self.zci.push()
        self.assertFalse(changed, "Script deletion detected outside of whitelist")

        Settings.SCRIPT_WHITELIST = (
            "Traceroute,Ping,Detect operating system,Detect operating system (renamed)"
        )
        Settings.SYNC_SCRIPTS = False
        changed = await self.zci.push()
        self.assertFalse(changed, "Script deletion detected when sync is disabled")

        Settings.SYNC_SCRIPTS = True


if __name__ == "__main__":
    unittest.main()
