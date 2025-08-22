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

            if Settings.SCRIPT_WITHOUT_USRGRP and script_object.usrgrpid:
                script_object.usrgrpid = self._zabbix.get_user_group(
                    Settings.SCRIPT_DEFAULT_USRGRP
                )["name"]
            elif script_object.usrgrpid:
                script_object.usrgrpid = self._zabbix.get_user_group_id(
                    script_object.usrgrpid
                )["name"]

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
            logger.info("Detected change in script: %s", script.unique_name)

        def __import_script(script_obj: Script):
            script = Script(**script_obj.__dict__)

            logger.debug(
                "usrgrpid for script %s is %s", script.unique_name, script.usrgrpid
            )

            try:
                script.usrgrpid = self._zabbix.get_user_group(script.usrgrpid)[
                    "usrgrpid"
                ]
            except IndexError:
                logger.warning(
                    "User group not found for %s, using default %s. User group will not be synchronized with git",
                    script.unique_name,
                    Settings.SCRIPT_DEFAULT_USRGRP,
                )
                script.usrgrpid = self._zabbix.get_user_group(
                    Settings.SCRIPT_DEFAULT_USRGRP
                )["usrgrpid"]

            if script.unique_name in [t.unique_name for t in script_objects]:
                logger.info("Updating: %s", script.unique_name)

                old_script = next(
                    filter(
                        lambda dt: dt.unique_name == script.unique_name
                        and script.menu_path == dt.menu_path,
                        script_objects,
                    )
                )

                return self._zabbix.update_script(
                    {
                        "scriptid": old_script.scriptid,
                        **script.zabbix_dict,
                    }
                )
            else:
                logger.info("Creating: %s", script.unique_name)
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
                        script.unique_name,
                    )
                    logger.debug("Error details: %s", e)
                    failed_scripts.append(script)

        if len(failed_scripts):
            for script in failed_scripts:
                try:
                    __import_script(script)
                except Exception as e:
                    logger.exception(
                        "Error importing script %s: %s", script.unique_name, e
                    )

        return [t.unique_name for t in scripts]

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

            if script.unique_name in imported_script_names:
                logger.debug(
                    "Script %s was just imported, skipping deletion", script.unique_name
                )
                continue

            deletion_queue.append(script.unique_name)
            logger.info("Added %s to deletion queue", script.unique_name)

        if len(deletion_queue):
            script_ids = [
                t.scriptid
                for t in list(
                    filter(lambda dt: dt.unique_name in deletion_queue, script_objects)
                )
            ]

            logger.info("Deleting %s script(s) from Zabbix", len(script_ids))

            if len(script_ids):
                if not Settings.DRY_RUN:
                    self._zabbix.delete_scripts(script_ids)

        return deletion_queue
