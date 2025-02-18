import unittest
from os import getenv

from base_images import BaseImages

from zabbixci.settings import Settings

DEV_ZABBIX_URL = getenv("ZABBIX_URL")
DEV_ZABBIX_TOKEN = getenv("ZABBIX_TOKEN")
DEV_GIT_REMOTE = getenv("REMOTE")


class TestImagesBlacklist(BaseImages, unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        super().setUp()
        Settings.REGEX_MATCHING = True
        Settings.IMAGE_BLACKLIST = "retigra.*"

    async def test_image_delete(self):
        image_id = self.zci._zabbix.get_images(["retigra_(200)"])[0]["imageid"]
        self.zci._zabbix.delete_images([image_id])

        changed = await self.zci.push()
        self.assertFalse(changed, "Blacklisted image was deleted")

        changed = await self.zci.pull()
        self.assertFalse(changed, "Blacklisted image was imported")
