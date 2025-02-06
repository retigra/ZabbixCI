import unittest
from os import getenv

from base_templates import BaseTemplates

from zabbixci.settings import Settings

DEV_ZABBIX_URL = getenv("ZABBIX_URL")
DEV_ZABBIX_TOKEN = getenv("ZABBIX_TOKEN")
DEV_GIT_REMOTE = getenv("REMOTE")


class TestTemplatesWhitelist(BaseTemplates, unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        super().setUp()
        Settings.TEMPLATE_WHITELIST = "Linux by Zabbix agent,Linux by Zabbix 00000,Windows by Zabbix agent,Acronis Cyber Protect Cloud by HTTP,Kubernetes API server by HTTP,Kubernetes cluster state by HTTP"

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
