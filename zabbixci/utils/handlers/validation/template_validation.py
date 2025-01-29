import logging

from ruamel.yaml import YAML

from zabbixci.settings import Settings
from zabbixci.utils.handlers.validation import Handler

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
