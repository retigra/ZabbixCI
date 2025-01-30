import logging
import os
import unittest
from os import getenv

from test_templates import TestTemplates

from zabbixci import ZabbixCI
from zabbixci.settings import Settings
from zabbixci.utils.cache.cache import Cache
from zabbixci.utils.cache.cleanup import Cleanup

DEV_ZABBIX_URL = getenv("ZABBIX_URL")
DEV_ZABBIX_TOKEN = getenv("ZABBIX_TOKEN")
DEV_GIT_REMOTE = getenv("REMOTE")


class TestTemplatesWhitelistRegex(TestTemplates):
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
        # Settings.TEMPLATE_WHITELIST = "Linux by Zabbix agent,Linux by Zabbix 00000,Windows by Zabbix agent,Acronis Cyber Protect Cloud by HTTP,Kubernetes API server by HTTP,Kubernetes cluster state by HTTP"

        Settings.TEMPLATE_WHITELIST = "(Linux|Windows|Acronis|Kubernetes).*"

        self.zci = ZabbixCI()

    # Test template deletion with whitelist checks
    async def test_template_delete(self):
        # Delete a template
        template_id = self.zci._zabbix.get_templates_name(
            ["Acronis Cyber Protect Cloud by HTTP"]
        )[0]["templateid"]
        self.zci._zabbix.delete_templates([template_id])

        Settings.TEMPLATE_WHITELIST = "Acronis Cyber"  # Should not match partial names

        # Push changes to git
        changed = await self.zci.push()
        self.assertFalse(changed, "Template deletion detected outside of whitelist")

        Settings.TEMPLATE_WHITELIST = "Linux by Zabbix agent,Linux by Zabbix 00000,Windows by Zabbix agent,Acronis Cyber Protect Cloud by HTTP,Kubernetes API server by HTTP,Kubernetes cluster state by HTTP"

        Settings.PULL_BRANCH = "test"

        changed = await self.zci.pull()
        self.assertTrue(changed, "Template was not restored")

        Settings.PULL_BRANCH = "main"
        changed = await self.zci.pull()
        self.assertTrue(changed, "Template deletion from Git was not detected")

        await self.restoreState()


if __name__ == "__main__":
    unittest.main()
