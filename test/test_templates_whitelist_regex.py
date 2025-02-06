import unittest
from os import getenv

from base_templates import BaseTemplates

from zabbixci.settings import Settings

DEV_ZABBIX_URL = getenv("ZABBIX_URL")
DEV_ZABBIX_TOKEN = getenv("ZABBIX_TOKEN")
DEV_GIT_REMOTE = getenv("REMOTE")


class TestTemplatesWhitelistRegex(BaseTemplates, unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        super().setUp()
        Settings.REGEX_MATCHING = True
        Settings.TEMPLATE_WHITELIST = "(Linux|Windows|Acronis|Kubernetes).*"

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


if __name__ == "__main__":
    unittest.main()
