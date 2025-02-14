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
        Settings.IMAGE_BLACKLIST = "Non Existent"
