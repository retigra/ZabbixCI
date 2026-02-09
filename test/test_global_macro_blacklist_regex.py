import unittest
from os import getenv

from base_global_macro import BaseGlobalMacro

DEV_ZABBIX_URL = getenv("ZABBIX_URL")
DEV_ZABBIX_TOKEN = getenv("ZABBIX_TOKEN")
DEV_GIT_REMOTE = getenv("REMOTE")


class TestGlobalMacroBlacklistRegex(BaseGlobalMacro, unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        super().setUp()
        self.settings.REGEX_MATCHING = True
        self.settings.GLOBAL_MACRO_BLACKLIST = r"{\$TEST_.*}"


if __name__ == "__main__":
    unittest.main()
