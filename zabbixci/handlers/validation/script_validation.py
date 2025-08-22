import logging

from ruamel.yaml import YAML

from zabbixci.assets.script import Script
from zabbixci.cache.filesystem import Filesystem
from zabbixci.handlers.validation.validation_handler import Handler
from zabbixci.settings import Settings

logger = logging.getLogger(__name__)
yaml = YAML()


class ScriptValidationHandler(Handler):
    """
    Handler for importing scripts into Zabbix based on changed files. Includes validation steps based on settings.

    :param zabbix: Zabbix instance
    """

    def get_whitelist(self):
        return Settings.get_script_whitelist()

    def get_blacklist(self):
        return Settings.get_script_blacklist()

    def read_validation(self, changed_file: str) -> bool:
        """
        Validation steps to perform on a changed file before it is processed as a script
        """
        if not changed_file.endswith(".yaml"):
            return False

        # Check if file is within the desired path
        if not Filesystem.is_within(
            changed_file, f"{Settings.CACHE_PATH}/{Settings.SCRIPT_PREFIX_PATH}"
        ):
            logger.debug("Skipping .yaml file %s outside of prefix path", changed_file)
            return False

        return True

    def object_validation(self, script: Script | None) -> bool:
        """
        White/blacklist validation for scripts
        """
        if not script:
            return False

        if self.enforce_blacklist(script.unique_name):
            logger.debug("Skipping blacklisted script: %s", script.unique_name)
            return False

        if self.enforce_whitelist(script.unique_name):
            logger.debug("Skipping non whitelisted script: %s", script.unique_name)
            return False

        return True
