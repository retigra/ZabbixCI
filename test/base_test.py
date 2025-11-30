import logging
import os

from zabbixci.cache.cache import Cache
from zabbixci.cache.cleanup import Cleanup
from zabbixci.settings import ApplicationSettings


class BaseTest:
    settings: ApplicationSettings

    def prep(self):
        cache_path = os.getenv("CACHE_PATH")
        self.settings = ApplicationSettings()

        if cache_path:
            self.settings.CACHE_PATH = cache_path
        self.cache = Cache(self.settings.CACHE_PATH)

        if os.path.exists(self.settings.CACHE_PATH):
            Cleanup.cleanup_cache(self.settings, full=True)

        logging.basicConfig(
            level=logging.ERROR,
            format="%(asctime)s - %(name)s - %(message)s",
        )
