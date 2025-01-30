import logging
import os
import unittest
from os import getenv
from test.test_templates import TestTemplates

from zabbixci import ZabbixCI
from zabbixci.settings import Settings
from zabbixci.utils.cache.cache import Cache
from zabbixci.utils.cache.cleanup import Cleanup

DEV_ZABBIX_URL = getenv("ZABBIX_URL")
DEV_ZABBIX_TOKEN = getenv("ZABBIX_TOKEN")
DEV_GIT_REMOTE = getenv("REMOTE")


class TestTemplatesBlacklistRegex(TestTemplates):
    def setUp(self):
        Settings.CACHE_PATH = "/tmp/zabbixci"
        self.cache = Cache(Settings.CACHE_PATH)

        if os.path.exists(Settings.CACHE_PATH):
            Cleanup.cleanup_cache(full=True)

        logging.basicConfig(
            level=logging.ERROR,
            format="%(asctime)s - %(name)s - %(message)s",
        )

        zci_log = logging.getLogger("zabbixci")
        zci_log.setLevel(logging.DEBUG)

        Settings.ZABBIX_URL = DEV_ZABBIX_URL
        Settings.ZABBIX_TOKEN = DEV_ZABBIX_TOKEN
        Settings.REMOTE = DEV_GIT_REMOTE
        Settings.SET_VERSION = True
        Settings.REGEX_MATCHING = True
        Settings.TEMPLATE_BLACKLIST = "Non .*"

        self.zci = ZabbixCI()


if __name__ == "__main__":
    unittest.main()
