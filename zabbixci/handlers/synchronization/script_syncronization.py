import logging

from zabbixci.assets.script import Script
from zabbixci.handlers.validation.script_validation import ScriptValidationHandler
from zabbixci.settings import Settings
from zabbixci.zabbix.zabbix import Zabbix

logger = logging.getLogger(__name__)


class ScriptHandler(ScriptValidationHandler):
    """
    Handler for importing scripts into Zabbix based on changed files. Includes validation steps based on settings.

    :param zabbix: Zabbix instance
    """

    _zabbix: Zabbix

    def __init__(self, zabbix: Zabbix):
        self._zabbix = zabbix

    def script_to_cache(self) -> list[Script]:
        """
        Export Zabbix scripts to cache.
        """
        if not Settings.SYNC_SCRIPTS:
            return []

        search = (
            self.get_whitelist()
            if not self._use_regex() and self.get_whitelist()
            else None
        )

        scripts = self._zabbix.get_scripts(search)

        logger.info("Found %s script(s) in Zabbix", len(scripts))

        script_objects = []

        for script in scripts:
            script_object = Script.from_zabbix(script)

            if not self.object_validation(script_object):
                continue

            script_object.save()
            script_objects.append(script_object)

        return script_objects

    def import_file_changes(
        self,
        changed_files: list[str],
        script_objects: list[Script],
    ) -> list[str]:
        """
        Import scripts into Zabbix based on changed files.

        :param changed_files: List of changed files
        :param script_objects: List of script objects from Zabbix, needed for choice between creation or update

        :return: List of imported script names
        """
        scripts: list[Script] = []

        if not Settings.SYNC_SCRIPTS:
            return []

        for file in changed_files:
            if not self.read_validation(file):
                continue

            script = Script.open(file)

            if not self.object_validation(script):
                continue

            scripts.append(script)
            logger.info("Detected change in script: %s", script.name)

        def __import_script(script: Script):
            if script.name in [t.name for t in script_objects]:
                logger.info("Updating: %s", script.name)

                old_script = next(
                    filter(lambda dt: dt.name == script.name, script_objects)
                )

                return self._zabbix.update_script(
                    {
                        "scriptid": old_script.scriptid,
                        **script.zabbix_dict,
                    }
                )
            else:
                logger.info("Creating: %s", script.name)
                return self._zabbix.create_script(script.zabbix_dict)

        failed_scripts: list[Script] = []

        # Import the scripts
        for script in scripts:
            if not Settings.DRY_RUN:
                try:
                    __import_script(script)
                except Exception as e:
                    logger.warning(
                        "Error importing script %s, will try to import later",
                        script.name,
                    )
                    logger.debug("Error details: %s", e)
                    failed_scripts.append(script)

        if len(failed_scripts):
            for script in failed_scripts:
                try:
                    __import_script(script)
                except Exception as e:
                    logger.error("Error importing script %s: %s", script.name, e)

        return [t.name for t in scripts]

    def delete_file_changes(
        self,
        deleted_files: list[str],
        imported_script_names: list[str],
        script_objects: list[Script],
    ):
        """
        Delete scripts from Zabbix based on deleted files.

        :param deleted_files: List of deleted files
        :param imported_script_names: List of imported script names
        :param script_objects: List of script objects from Zabbix, needed for deletion

        :return: List of deleted script names
        """
        deletion_queue: list[str] = []

        if not Settings.SYNC_SCRIPTS:
            return []

        for file in deleted_files:
            if not self.read_validation(file):
                continue

            script = Script.open(file)

            if not script:
                logger.warning("Could not open to be deleted file: %s", file)
                continue

            if not self.object_validation(script):
                continue

            if script.name in imported_script_names:
                logger.debug(
                    "Script %s was just imported, skipping deletion", script.name
                )
                continue

            deletion_queue.append(script.name)
            logger.info("Added %s to deletion queue", script.name)

        if len(deletion_queue):
            script_ids = [
                t.scriptid
                for t in list(
                    filter(lambda dt: dt.name in deletion_queue, script_objects)
                )
            ]

            logger.info("Deleting %s script(s) from Zabbix", len(script_ids))

            if len(script_ids):
                if not Settings.DRY_RUN:
                    self._zabbix.delete_scripts(script_ids)

        return deletion_queue
