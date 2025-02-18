import unittest
from os import getenv

from base_icon_map import BaseIconMap

DEV_ZABBIX_URL = getenv("ZABBIX_URL")
DEV_ZABBIX_TOKEN = getenv("ZABBIX_TOKEN")
DEV_GIT_REMOTE = getenv("REMOTE")


class TestIconMap(BaseIconMap, unittest.IsolatedAsyncioTestCase):
    pass
