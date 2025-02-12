import logging

from ruamel.yaml import YAML

from zabbixci.assets.template import Template
from zabbixci.cache.filesystem import Filesystem
from zabbixci.handlers.validation.validation_handler import Handler
from zabbixci.settings import Settings

logger = logging.getLogger(__name__)
yaml = YAML()


class TemplateValidationHandler(Handler):
    """
    Handler for importing templates into Zabbix based on changed files. Includes validation steps based on settings.

    :param zabbix: Zabbix instance
    """

    def get_whitelist(self):
        return Settings.get_template_whitelist()

    def get_blacklist(self):
        return Settings.get_template_blacklist()

    def read_validation(self, changed_file: str) -> bool:
        """
        Validation steps to perform on a changed file before it is processed as a template
        """
        if not changed_file.endswith(".yaml"):
            return False

        # Check if file is within the desired path
        if not Filesystem.is_within(
            changed_file, f"{Settings.CACHE_PATH}/{Settings.TEMPLATE_PREFIX_PATH}"
        ):
            logger.debug(f"Skipping .yaml file {changed_file} outside of prefix path")
            return False

        return True

    def object_validation(self, template: Template | None) -> bool:
        """
        White/blacklist validation for templates
        """
        if not template:
            return False

        if self.enforce_blacklist(template.name):
            logger.debug(f"Skipping blacklisted template: {template.name}")
            return False

        if self.enforce_whitelist(template.name):
            logger.debug(f"Skipping non whitelisted template: {template.name}")
            return False

        return True
