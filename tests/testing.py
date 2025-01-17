import logging
import os
import unittest
from os import getenv

from zabbixci import ZabbixCI
from zabbixci.settings import Settings

DEV_ZABBIX_URL = getenv("ZABBIX_URL")
DEV_ZABBIX_TOKEN = getenv("ZABBIX_TOKEN")
DEV_GIT_REMOTE = getenv("REMOTE")


class TestPushFunctions(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        if os.path.exists(".cache"):
            ZabbixCI.cleanup_cache(full=True)

        logging.basicConfig(
            level=logging.ERROR,
            format="%(asctime)s - %(name)s - %(message)s",
        )

        Settings.ZABBIX_URL = DEV_ZABBIX_URL
        Settings.ZABBIX_TOKEN = DEV_ZABBIX_TOKEN
        Settings.REMOTE = DEV_GIT_REMOTE
        Settings.TEMPLATE_WHITELIST = "Linux by Zabbix agent,Linux by Zabbix 00000,Windows by Zabbix agent,Acronis Cyber Protect Cloud by HTTP,Kubernetes API server by HTTP,Kubernetes cluster state by HTTP"

        self.zci = ZabbixCI()

    async def restoreState(self):
        ZabbixCI.cleanup_cache()

        # Restore Zabbix to initial testing state
        Settings.PULL_BRANCH = "test"
        await self.zci.pull()

        Settings.PULL_BRANCH = "main"
        await self.zci.push()

    async def asyncSetUp(self):
        await self.zci.create_zabbix()

        await self.restoreState()

    async def test_push_pull_remote_defaults(self):
        # Push default Zabbix templates to remote
        await self.zci.push()

        # No changed when we have just pushed
        changed = await self.zci.pull()
        self.assertFalse(changed)

    async def test_template_change(self):
        # Rename a template
        id = self.zci._zabbix.get_templates_name(["Windows by Zabbix agent"])[0][
            "templateid"
        ]
        self.zci._zabbix.set_template(id, {"name": "Windows by Zabbix agent (renamed)"})

        # Push changes to git
        changed = await self.zci.push()
        self.assertTrue(changed, "Template change not detected")

        # Revert changes in Zabbix
        self.zci._zabbix.set_template(id, {"name": "Windows by Zabbix agent"})

        # Restore to Git version
        changed = await self.zci.pull()
        self.assertTrue(changed, "Template was not restored")

        # Assert Git version is imported back into Zabbix
        matches = self.zci._zabbix.get_templates_filtered(
            [Settings.ROOT_TEMPLATE_GROUP], ["Windows by Zabbix agent"]
        )
        self.assertEqual(len(matches), 1, "Template not found")
        self.assertEqual(
            matches[0]["name"],
            "Windows by Zabbix agent (renamed)",
            "Template name not restored",
        )

        await self.restoreState()

    async def test_template_rename(self):
        # Rename a template
        id = self.zci._zabbix.get_templates_name(["Linux by Zabbix agent"])[0][
            "templateid"
        ]
        self.zci._zabbix.set_template(id, {"host": "Linux by Zabbix 00000"})

        # Push changes to git
        changed = await self.zci.push()
        self.assertTrue(changed, "Renaming not detected")

        # Make changes in Zabbix
        self.zci._zabbix.set_template(id, {"host": "Linux by Zabbix agent"})

        # Restore to Git version
        changed = await self.zci.pull()
        self.assertTrue(changed, "Template was not restored")

        # Assert Git version is restored
        matches = self.zci._zabbix.get_templates_filtered(
            [Settings.ROOT_TEMPLATE_GROUP], ["Linux by Zabbix 00000"]
        )
        self.assertEqual(len(matches), 1, "Template not found")

        await self.restoreState()

    async def test_template_delete(self):
        # Delete a template
        id = self.zci._zabbix.get_templates_name(
            ["Acronis Cyber Protect Cloud by HTTP"]
        )[0]["templateid"]
        self.zci._zabbix.delete_template([id])

        # Push changes to git
        changed = await self.zci.push()
        self.assertTrue(changed, "Deletion from Zabbix not detected")

        Settings.PULL_BRANCH = "test"

        changed = await self.zci.pull()
        self.assertTrue(changed, "Template was not restored")

        Settings.PULL_BRANCH = "main"
        changed = await self.zci.pull()
        self.assertTrue(changed, "Template deletion from Git was not detected")

        await self.restoreState()

    async def test_push_to_new_branch(self):
        Settings.PUSH_BRANCH = "new-branch"

        # Push default Zabbix templates to remote
        await self.zci.push()

        Settings.PUSH_BRANCH = "main"

        await self.restoreState()

    async def asyncTearDown(self):
        await self.zci._zabbix.zapi.logout()

        # Close custom session, if it exists
        if self.zci._zabbix._client_session:
            await self.zci._zabbix._client_session.close()


if __name__ == "__main__":
    unittest.main()
