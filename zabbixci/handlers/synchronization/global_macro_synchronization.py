import logging

from zabbixci.assets.global_macro import HIDDEN_VALUE, SECRET_TYPE, GlobalMacro
from zabbixci.handlers.validation.global_macro_validation import (
    GlobalMacroValidationHandler,
)
from zabbixci.settings import ApplicationSettings
from zabbixci.zabbix.zabbix import Zabbix

logger = logging.getLogger(__name__)


class GlobalMacroHandler(GlobalMacroValidationHandler):
    """
    Handler for importing global macros into Zabbix based on changed files.
    """

    _zabbix: Zabbix

    def __init__(self, zabbix: Zabbix, settings: ApplicationSettings):
        super().__init__(settings)
        self._zabbix = zabbix

    def global_macros_to_cache(self) -> list[GlobalMacro]:
        """
        Export Zabbix global macros to the cache.
        """
        if not self.settings.SYNC_GLOBAL_MACROS:
            return []

        search = (
            self.get_whitelist()
            if not self._use_regex() and self.get_whitelist()
            else None
        )

        macros = self._zabbix.get_global_macros(search)

        logger.info("Found %s global macro(s) in Zabbix", len(macros))

        macro_objects: list[GlobalMacro] = []

        for macro in macros:
            macro_object = GlobalMacro.from_zabbix(macro)

            if not macro_object:
                continue

            if not self.object_validation(macro_object):
                continue

            macro_object.save(self.settings)
            macro_objects.append(macro_object.minify())

        return macro_objects

    def import_file_changes(
        self,
        changed_files: list[str],
        macro_objects: list[GlobalMacro],
    ) -> list[str]:
        """
        Import global macros into Zabbix based on changed files.
        """
        if not self.settings.SYNC_GLOBAL_MACROS:
            return []

        macros: list[GlobalMacro] = []
        skipped_secret_macros: list[str] = []

        for file in changed_files:
            if not self.read_validation(file):
                continue

            macro = GlobalMacro.open(file)

            if not self.object_validation(macro):
                continue

            if macro and (macro.type == SECRET_TYPE or macro.value == HIDDEN_VALUE):
                skipped_secret_macros.append(macro.name)
                logger.warning(
                    "Skipping secret global macro %s to avoid overwriting its value",
                    macro.name,
                )
                continue

            if macro:
                macros.append(macro)
                logger.info("Detected change in global macro: %s", macro.name)

        def __import_macro(macro: GlobalMacro):
            existing = next((m for m in macro_objects if m.name == macro.name), None)
            if existing and existing.global_macro_id:
                logger.info("Updating global macro: %s", macro.name)
                return self._zabbix.update_global_macro(
                    {
                        "globalmacroid": str(existing.global_macro_id),
                        "value": macro.value,
                        "description": macro.description,
                        "type": int(macro.type),
                    }
                )

            logger.info("Creating global macro: %s", macro.name)
            return self._zabbix.create_global_macro(macro.zabbix_create_dict)

        failed_macros: list[GlobalMacro] = []

        for macro in macros:
            if self.settings.DRY_RUN:
                continue

            try:
                __import_macro(macro)
            except Exception as e:  # pragma: no cover - defensive retry pattern
                logger.warning(
                    "Error importing global macro %s, will try to import later",
                    macro.name,
                )
                logger.debug("Error details: %s", e)
                failed_macros.append(macro)

        if failed_macros and not self.settings.DRY_RUN:
            for macro in failed_macros:
                try:
                    __import_macro(macro)
                except Exception as e:  # pragma: no cover - defensive retry pattern
                    logger.error("Error importing global macro %s: %s", macro.name, e)

        if skipped_secret_macros:
            logger.info(
                "Skipped %s secret global macro(s)",
                len(skipped_secret_macros),
            )

        return [m.name for m in macros]

    def delete_file_changes(
        self,
        deleted_files: list[str],
        imported_macro_names: list[str],
        macro_objects: list[GlobalMacro],
    ) -> list[str]:
        """
        Delete global macros from Zabbix based on deleted files.
        """
        if not self.settings.SYNC_GLOBAL_MACROS:
            return []

        deletion_queue: list[str] = []

        for file in deleted_files:
            if not self.read_validation(file):
                continue

            macro = GlobalMacro.partial_open(file)

            if not macro:
                logger.warning(
                    "Could not open macro file slated for deletion: %s", file
                )
                continue

            if not self.object_validation(macro):
                continue

            if macro.name in imported_macro_names:
                logger.debug(
                    "Global macro %s was just imported, skipping deletion", macro.name
                )
                continue

            deletion_queue.append(macro.name)
            logger.info("Added global macro %s to deletion queue", macro.name)

        if deletion_queue:
            macro_ids = [
                m.global_macro_id
                for m in macro_objects
                if m.name in deletion_queue and m.global_macro_id
            ]

            logger.info("Deleting %s global macro(s) from Zabbix", len(macro_ids))

            if macro_ids and not self.settings.DRY_RUN:
                self._zabbix.delete_global_macros([int(mid) for mid in macro_ids])

        return deletion_queue
