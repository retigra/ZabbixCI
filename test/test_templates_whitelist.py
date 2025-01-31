import logging
import os
import unittest
from os import getenv

from base_templates import BaseTemplates

from zabbixci import ZabbixCI
from zabbixci.settings import Settings
from zabbixci.utils.cache.cache import Cache
from zabbixci.utils.cache.cleanup import Cleanup

DEV_ZABBIX_URL = getenv("ZABBIX_URL")
DEV_ZABBIX_TOKEN = getenv("ZABBIX_TOKEN")
DEV_GIT_REMOTE = getenv("REMOTE")


class TestTemplatesWhitelist(BaseTemplates, unittest.IsolatedAsyncioTestCase):
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
        Settings.SET_VERSION = True
        Settings.REGEX_MATCHING = False
        Settings.TEMPLATE_WHITELIST = "Linux by Zabbix agent,Linux by Zabbix 00000,Windows by Zabbix agent,Acronis Cyber Protect Cloud by HTTP,Kubernetes API server by HTTP,Kubernetes cluster state by HTTP"

        self.zci = ZabbixCI()

    # Test template deletion with whitelist checks
    async def test_template_delete(self):
        # Delete a template
        template_id = self.zci._zabbix.get_templates_name(
            ["Acronis Cyber Protect Cloud by HTTP"]
        )[0]["templateid"]
        self.zci._zabbix.delete_templates([template_id])

        Settings.TEMPLATE_WHITELIST = "Nonexistent template"

        # Push changes to git
        changed = await self.zci.push()
        self.assertFalse(changed, "Template deletion detected outside of whitelist")

        Settings.TEMPLATE_WHITELIST = "Linux by Zabbix agent,Linux by Zabbix 00000,Windows by Zabbix agent,Acronis Cyber Protect Cloud by HTTP,Kubernetes API server by HTTP,Kubernetes cluster state by HTTP"
        Settings.SYNC_TEMPLATES = False
        changed = await self.zci.push()
        self.assertFalse(changed, "Template deletion detected when sync is disabled")

        Settings.SYNC_TEMPLATES = True


if __name__ == "__main__":
    unittest.main()
