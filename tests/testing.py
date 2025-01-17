import logging
import os
import unittest
from os import getenv

from zabbixci import ZabbixCI
from zabbixci.settings import Settings

DEV_ZABBIX_URL = getenv("ZABBIX_URL")
DEV_ZABBIX_TOKEN = getenv("ZABBIX_TOKEN")
DEV_GIT_REMOTE = getenv("GIT_REMOTE")


class TestPushFunctions(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        if os.path.exists(".cache"):
            ZabbixCI.cleanup_cache(full=True)

        logging.basicConfig(
            format="%(asctime)s [%(name)s]  [%(levelname)s]: %(message)s",
            level=logging.INFO,
        )

        zabbixci_logger = logging.getLogger("zabbixci")
        zabbixci_logger.setLevel(logging.DEBUG)

        Settings.ZABBIX_URL = DEV_ZABBIX_URL
        Settings.ZABBIX_TOKEN = DEV_ZABBIX_TOKEN
        Settings.REMOTE = DEV_GIT_REMOTE
        Settings.TEMPLATE_WHITELIST = [
            "Linux by Zabbix agent",
            "Windows by Zabbix agent moved",
            "Acronis Cyber Protect Cloud by HTTP",
            "Kubernetes API server by HTTP",
            "Kubernetes cluster state by HTTP",
        ]

        self.zci = ZabbixCI()

    async def asyncSetUp(self):
        await self.zci.create_zabbix()

    async def test_push_pull_remote_defaults(self):
        # Push default Zabbix templates to remote
        await self.zci.push()

        # No changed when we have just pushed
        changed = await self.zci.pull()
        self.assertFalse(changed)

    async def test_template_change(self):
        # Rename a template
        id = self.zci._zabbix.get_templates_name(["Linux by Zabbix agent"])[0][
            "templateid"
        ]
        self.zci._zabbix.set_template(id, {"name": "Linux by Zabbix agent (renamed)"})

        # Push changes to git
        changed = await self.zci.push()
        self.assertTrue(changed)

        # Make changes in Zabbix
        self.zci._zabbix.set_template(id, {"name": "Linux by Zabbix agent"})

        # Restore to Git version
        changed = await self.zci.pull()
        self.assertTrue(changed)

        # Assert Git version is restored
        matches = self.zci._zabbix.get_templates_filtered(
            [Settings.ROOT_TEMPLATE_GROUP], ["Linux by Zabbix agent"]
        )
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["name"], "Linux by Zabbix agent (renamed)")

        # Restore original name
        self.zci._zabbix.set_template(id, {"name": "Linux by Zabbix agent"})
        changed = await self.zci.push()
        self.assertTrue(changed)

    async def test_template_rename(self):
        # Rename a template
        id = self.zci._zabbix.get_templates_name(["Linux by Zabbix agent"])[0][
            "templateid"
        ]
        self.zci._zabbix.set_template(id, {"host": "Linux by Zabbix agent moved"})

        # Push changes to git
        changed = await self.zci.push()
        self.assertTrue(changed)

        # Make changes in Zabbix
        self.zci._zabbix.set_template(id, {"host": "Linux by Zabbix agent"})

        # Restore to Git version
        changed = await self.zci.pull()
        self.assertTrue(changed)

        # Assert Git version is restored
        matches = self.zci._zabbix.get_templates_filtered(
            [Settings.ROOT_TEMPLATE_GROUP], ["Linux by Zabbix agent"]
        )
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["host"], "Linux by Zabbix agent moved")

        # Restore original name
        self.zci._zabbix.set_template(id, {"host": "Linux by Zabbix agent"})
        changed = await self.zci.push()
        self.assertTrue(changed)

    async def asyncTearDown(self):
        await self.zci._zabbix.zapi.logout()

        # Close custom session, if it exists
        if self.zci._zabbix._client_session:
            await self.zci._zabbix._client_session.close()


if __name__ == "__main__":
    unittest.main()
