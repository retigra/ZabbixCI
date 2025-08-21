import unittest
from os import getenv

from base_scripts import BaseScripts

DEV_ZABBIX_URL = getenv("ZABBIX_URL")
DEV_ZABBIX_TOKEN = getenv("ZABBIX_TOKEN")
DEV_GIT_REMOTE = getenv("REMOTE")


class TestScripts(BaseScripts, unittest.IsolatedAsyncioTestCase):
    pass
