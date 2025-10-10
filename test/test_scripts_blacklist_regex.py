import unittest
from os import getenv


from base_scripts import BaseScripts

from zabbixci.settings import Settings

DEV_ZABBIX_URL = getenv("ZABBIX_URL")
DEV_ZABBIX_TOKEN = getenv("ZABBIX_TOKEN")
DEV_GIT_REMOTE = getenv("REMOTE")


class TestScriptsBlacklistRegex(BaseScripts, unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        super().setUp()
        Settings.REGEX_MATCHING = True
        Settings.SCRIPT_BLACKLIST = r"Non .*"

    # Test script deletion with whitelist checks
    async def test_script_delete(self):
        # Delete a script
        script_id = self.zci._zabbix.get_scripts(["Traceroute"])[0]["scriptid"]
        self.zci._zabbix.delete_scripts([script_id])

        Settings.SCRIPT_BLACKLIST = r"Traceroute"

        # Push changes to git
        changed = await self.zci.push()
        self.assertFalse(changed, "Script deletion detected inside of blacklist")


if __name__ == "__main__":
    unittest.main()
