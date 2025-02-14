import unittest
from os import getenv

from base_images import BaseImages

DEV_ZABBIX_URL = getenv("ZABBIX_URL")
DEV_ZABBIX_TOKEN = getenv("ZABBIX_TOKEN")
DEV_GIT_REMOTE = getenv("REMOTE")


class TestImages(BaseImages, unittest.IsolatedAsyncioTestCase):
    pass
