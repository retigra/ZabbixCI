import logging

from zabbixci.assets.global_macro import GlobalMacro
from zabbixci.cache.filesystem import Filesystem
from zabbixci.handlers.validation.validation_handler import Handler
from zabbixci.settings import Settings

logger = logging.getLogger(__name__)


class GlobalMacroValidationHandler(Handler):
    """
    Validation handler for global macros.
    """

    def get_whitelist(self):
        return Settings.get_global_macro_whitelist()

    def get_blacklist(self):
        return Settings.get_global_macro_blacklist()

    def read_validation(self, changed_file: str) -> bool:
        """
        Validation steps to perform on a changed file before it is processed as a macro.
        """
        if not changed_file.endswith(".yaml"):
            return False

        if not Filesystem.is_within(
            changed_file, f"{Settings.CACHE_PATH}/{Settings.GLOBAL_MACRO_PREFIX_PATH}"
        ):
            logger.debug(
                "Skipping .yaml file %s outside of global macro prefix path",
                changed_file,
            )
            return False

        return True

    def object_validation(self, macro: GlobalMacro | None) -> bool:
        if not macro:
            return False

        if self.enforce_whitelist(macro.name):
            logger.debug("Skipping macro %s not in whitelist", macro.name)
            return False

        if self.enforce_blacklist(macro.name):
            logger.debug("Skipping macro %s in blacklist", macro.name)
            return False

        return True

