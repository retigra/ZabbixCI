import unittest
from os import getenv

from base_images import BaseImages

from zabbixci.settings import Settings

DEV_ZABBIX_URL = getenv("ZABBIX_URL")
DEV_ZABBIX_TOKEN = getenv("ZABBIX_TOKEN")
DEV_GIT_REMOTE = getenv("REMOTE")


class TestImageWhitelist(BaseImages, unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        super().setUp()
        Settings.IMAGE_WHITELIST = "Cloud_(24),Cloud_(48),Cloud_(64),Cloud_(96),Cloud_(128),Cloud_(128) (renamed),retigra_(200)"
