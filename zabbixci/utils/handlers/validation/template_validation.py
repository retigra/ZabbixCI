import logging

from ruamel.yaml import YAML

from zabbixci.settings import Settings
from zabbixci.utils.cache.filesystem import Filesystem
from zabbixci.utils.handlers.validation import Handler
from zabbixci.utils.services.template import Template

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

    def template_validation(self, template: Template) -> bool:
        """
        White/blacklist validation for templates
        """
        if self.enforce_blacklist(template.name):
            logger.debug(f"Skipping blacklisted template {template.name}")
            return False

        if self.enforce_whitelist(template.name):
            logger.debug(f"Skipping non whitelisted template {template.name}")
            return False

        return True
