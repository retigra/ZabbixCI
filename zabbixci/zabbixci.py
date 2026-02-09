import logging
import os
import ssl
from datetime import datetime, timezone

from pygit2.enums import FileStatus, ResetMode
from regex import search
from ruamel.yaml import YAML

from zabbixci.assets import Template
from zabbixci.cache.cleanup import Cleanup
from zabbixci.git import Git, GitCredentials
from zabbixci.handlers.synchronization.global_macro_synchronization import (
    GlobalMacroHandler,
)
from zabbixci.handlers.synchronization.icon_map_synchronization import IconMapHandler
from zabbixci.handlers.synchronization.image_synchronization import ImageHandler
from zabbixci.handlers.synchronization.script_synchronization import ScriptHandler
from zabbixci.handlers.synchronization.template_synchronization import TemplateHandler
from zabbixci.settings import ApplicationSettings
from zabbixci.zabbix import Zabbix, ZabbixConstants


class ZabbixCI:
    logger = logging.getLogger(__name__)
    yaml = YAML()

    _zabbix: Zabbix
    _git: Git
    _ssl_context: ssl.SSLContext | None = None

    settings: ApplicationSettings

    def __init__(self, settings: ApplicationSettings, logger=None):
        self.settings = settings

        if logger:
            self.logger = logger

    @classmethod
    def copy(cls, instance: "ZabbixCI") -> "ZabbixCI":
        """
        Create a copy of the ZabbixCI instance, shares the Zabbix and Git objects with the original
        """
        new_instance = cls(instance.settings)
        new_instance._zabbix = instance._zabbix
        new_instance._git = instance._git
        return new_instance

    async def create_zabbix(self) -> None:
        """
        Create a Zabbix object with the appropriate credentials
        """
        # Construct the SSL context if a CA bundle is provided

        if self.settings.CA_BUNDLE:
            self._ssl_context = ssl.create_default_context()
            self._ssl_context.load_verify_locations(self.settings.CA_BUNDLE)

        self._zabbix = Zabbix(
            url=self.settings.ZABBIX_URL,
            validate_certs=not self.settings.INSECURE_SSL_VERIFY,
            ssl_context=self._ssl_context,
            skip_version_check=self.settings.SKIP_VERSION_CHECK,
            **self.settings.ZABBIX_KWARGS,
        )

        if self.settings.ZABBIX_TOKEN:
            self.logger.debug("Using token for Zabbix authentication")
            await self._zabbix.zapi.login(token=self.settings.ZABBIX_TOKEN)
        elif self.settings.ZABBIX_USER and self.settings.ZABBIX_PASSWORD:
            self.logger.debug("Using username and password for Zabbix authentication")
            await self._zabbix.zapi.login(
                user=self.settings.ZABBIX_USER,
                password=self.settings.ZABBIX_PASSWORD,
            )

        if self._zabbix.zapi.version < ZabbixConstants.MINIMAL_VERSION:
            self.logger.error(
                "Zabbix server version %s is not supported (6.0+ required)",
                self._zabbix.zapi.version,
            )
            raise SystemExit(1)

    def create_git(self, git_cb=None) -> None:
        """
        Create a Git object with the appropriate credentials
        """
        if git_cb is None:
            git_cb = GitCredentials(self.settings).create_git_callback()

        self._git = Git(
            self.settings.CACHE_PATH, git_cb, self.settings, **self.settings.GIT_KWARGS
        )

    async def push(self) -> bool:
        """
        Fetch Zabbix state and commit changes to git remote
        """
        if not self._git or not self._zabbix:
            raise ValueError(
                "ZabbixCI has not been initialized, call create_zabbix() and create_git() first"
            )

        if not self.settings.REMOTE:
            raise ValueError("Remote repository not set")

        self._git.fetch(self.settings.REMOTE)

        if not self._git.is_empty:
            # If the repository is empty, new branches can't be created. But it is
            # safe to push to the default branch

            # Switch to the pull branch, as we base our push branch on it
            self._git.switch_branch(self.settings.PULL_BRANCH)

            # Switch or create the push branch
            self._git.switch_branch(self.settings.PUSH_BRANCH)

            # Pull the latest remote state
            try:
                self._git.pull(self.settings.REMOTE)
            except KeyError:
                self.logger.info(
                    "Remote branch does not exist, using state from branch: %s",
                    self.settings.PULL_BRANCH,
                )
                self._git.pull(self.settings.REMOTE, branch=self.settings.PULL_BRANCH)

        # Reflect current Zabbix state in the cache
        Cleanup.cleanup_cache(self.settings)

        template_handler = TemplateHandler(self._zabbix, self.settings)
        image_handler = ImageHandler(self._zabbix, self.settings)
        icon_map_handler = IconMapHandler(self._zabbix, self.settings)
        script_handler = ScriptHandler(self._zabbix, self.settings)
        macro_handler = GlobalMacroHandler(self._zabbix, self.settings)

        template_objects = await template_handler.templates_to_cache()
        image_objects = image_handler.images_to_cache()
        icon_map_handler.icon_map_to_cache(image_objects)
        script_handler.script_to_cache()
        macro_handler.global_macros_to_cache()

        # Check if there are any changes to commit
        if not self._git.has_changes and not self._git.ahead_of_remote:
            self.logger.info("No changes detected")
            return False

        self.logger.info("Remote differs from local state, preparing to push")
        change_amount = len(self._git.status())

        diff = self._git.diff()
        Git.print_diff(diff)

        # Check if we have any changes to commit. Otherwise, we just push the current state
        if self._git.has_changes:
            # Create a commit
            changes = self._git.status()

            regex_match = search("https?://([^/]+)", self._zabbix.zapi.url)

            host = os.getenv(
                "ZABBIX_HOST",
                regex_match.group(1) if regex_match else "zabbix_host",
            )

            change_amount = len(changes)

            for relative_path, status in changes.items():
                file = f"{self.settings.CACHE_PATH}/{relative_path}"

                if status == FileStatus.WT_DELETED:
                    self.logger.info("Detected deletion of: %s", file)
                    continue

                self.logger.info("Detected change in: %s", file)

                if not template_handler.read_validation(file):
                    continue

                template = Template.open(file, self.settings)

                if (
                    self.settings.VENDOR
                    and not template.vendor
                    and self._zabbix.api_version
                    >= ZabbixConstants.VENDOR_SUPPORTED_VERSION
                ):
                    set_vendor = self.settings.VENDOR
                    template.set_vendor(set_vendor)
                    self.logger.debug("Setting vendor to: %s", set_vendor)

                if (
                    self.settings.SET_VERSION
                    and self._zabbix.api_version
                    >= ZabbixConstants.VENDOR_SUPPORTED_VERSION
                ):
                    new_version = datetime.now(timezone.utc).strftime("%Y.%m.%d %H:%M")
                    template.set_version(new_version)
                    self.logger.debug("Setting version to: %s", new_version)

                if (template.new_version or template.new_vendor) and (
                    template.vendor and template.version
                ):
                    template.save()

                    if not self.settings.DRY_RUN:
                        self.logger.debug(
                            "Updating template metadata for: %s", template.name
                        )
                        self._zabbix.set_template(
                            next(
                                filter(
                                    lambda t: t["host"] == template.name,
                                    template_objects,
                                )
                            )["templateid"],
                            template.updated_items,
                        )

            if not self.settings.DRY_RUN:
                # Commit and push the changes
                self._git.add_all()

                # Generate commit message
                self._git.commit(
                    self.settings.GIT_COMMIT_MESSAGE
                    or f"Committed Zabbix state from {host}"
                )
                self.logger.info(
                    "Staged changes from %s committed to %s",
                    host,
                    self._git.current_branch,
                )
        else:
            self.logger.info("No staged changes, updating remote with current state")

        if not self.settings.DRY_RUN:
            self._git.push(self.settings.REMOTE)
            self.logger.info(
                "Committed %s new changes to %s:%s",
                change_amount,
                self.settings.REMOTE,
                self.settings.PUSH_BRANCH,
            )
        else:
            self.logger.info(
                "Dry run enabled, would have committed %s new changes to %s:%s",
                change_amount,
                self.settings.REMOTE,
                self.settings.PUSH_BRANCH,
            )

        return change_amount > 0

    async def pull(self) -> bool:
        """
        Pull current state from git remote and update Zabbix
        """
        if not self._git or not self._zabbix:
            raise ValueError(
                "ZabbixCI has not been initialized, call create_zabbix() and create_git() first"
            )

        if not self.settings.REMOTE:
            raise ValueError("Remote repository not set")

        self._git.switch_branch(self.settings.PULL_BRANCH)

        # Pull the latest remote state, untracked changes are preserved
        self._git.pull(self.settings.REMOTE)

        self._git.reset(
            self._git.lookup_reference(
                f"refs/remotes/origin/{self.settings.PULL_BRANCH}"
            ).target,
            ResetMode.HARD,
        )

        current_revision = self._git.get_current_revision()

        # Reflect current Zabbix state in the cache
        Cleanup.cleanup_cache(self.settings)

        template_handler = TemplateHandler(self._zabbix, self.settings)
        image_handler = ImageHandler(self._zabbix, self.settings)
        icon_map_handler = IconMapHandler(self._zabbix, self.settings)
        script_handler = ScriptHandler(self._zabbix, self.settings)
        macro_handler = GlobalMacroHandler(self._zabbix, self.settings)

        template_objects = await template_handler.templates_to_cache()
        image_objects = image_handler.images_to_cache()
        icon_map_objects = icon_map_handler.icon_map_to_cache(image_objects)
        script_objects = script_handler.script_to_cache()
        macro_objects = macro_handler.global_macros_to_cache()

        # Check if there are any changes to commit
        if self._git.has_changes:
            self.logger.info("Zabbix state is out of sync, syncing")

        status = self._git.status()

        # Get the changed files, we compare the untracked changes with the desired.
        # When we have a new untracked file, that means it was deleted in the desired state.
        changed_files: list[str] = [
            f"{self.settings.CACHE_PATH}/{path}"
            for path, flags in status.items()
            if flags in [FileStatus.WT_DELETED, FileStatus.WT_MODIFIED]
        ]
        deleted_files: list[str] = [
            f"{self.settings.CACHE_PATH}/{path}"
            for path, flags in status.items()
            if flags == FileStatus.WT_NEW
        ]

        self.logger.debug("Following files have changed on Git: %s", changed_files)
        self.logger.debug("Following files are deleted from Git: %s", deleted_files)

        diff = self._git.diff()
        Git.print_diff(diff, invert=True)

        # Store exported Zabbix state in a rollback branch
        if (
            self.settings.CREATE_ROLLBACK_BRANCH
            and not self.settings.DRY_RUN
            and self._git.has_changes
        ):
            operational_branch_name = self._git.current_branch

            rollback_branch_name = f"rollback/{self.settings.PULL_BRANCH}/{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            before_commit_revision = self._git.get_current_revision()
            self._git.switch_branch(rollback_branch_name)

            # Commit and push the changes
            self._git.add_all()

            # Generate commit message
            self._git.commit(
                self.settings.GIT_COMMIT_MESSAGE
                or f"Rollback commit of Zabbix state before pulling changes from {operational_branch_name}"
            )

            if self.settings.PUSH_ROLLBACK_BRANCH:
                self._git.force_push(
                    [f"refs/heads/{rollback_branch_name}"],
                    self.settings.REMOTE,
                )

            self.logger.info(
                "Created rollback branch %s from %s",
                rollback_branch_name,
                operational_branch_name,
            )

            # Switch back to operational branch and restore acquired files from Zabbix
            self._git.switch_branch(operational_branch_name)

            rollback_branch_id = self._git.lookup_reference(
                f"refs/heads/{rollback_branch_name}"
            ).target

            rollback_branch_oid = self._git.get(rollback_branch_id)
            self._git.checkout_tree(rollback_branch_oid)

            # Reset rollback commit to restore Zabbix changed files
            self._git.reset(before_commit_revision, ResetMode.MIXED)

        # Sync the file cache with the desired git state
        self._git.reset(current_revision, ResetMode.HARD)

        imported_template_ids, failed_template_names = (
            template_handler.import_file_changes(changed_files)
        )
        deleted_template_names = template_handler.delete_file_changes(
            deleted_files,
            [*imported_template_ids, *failed_template_names],
            template_objects,
        )

        imported_images = image_handler.import_file_changes(
            changed_files, image_objects
        )

        if imported_images:
            # Update available image objects (only needed for Zabbix image id's)
            image_objects = image_handler.images_to_cache()

        imported_icon_maps = icon_map_handler.import_file_changes(
            changed_files, icon_map_objects, image_objects
        )
        deleted_icon_map_names = icon_map_handler.delete_file_changes(
            deleted_files, imported_icon_maps, icon_map_objects
        )

        deleted_image_names = image_handler.delete_file_changes(
            deleted_files, imported_images, image_objects
        )

        imported_scripts = script_handler.import_file_changes(
            changed_files, script_objects
        )

        deleted_scripts = script_handler.delete_file_changes(
            deleted_files, imported_scripts, script_objects
        )
        imported_macros = macro_handler.import_file_changes(
            changed_files, macro_objects
        )
        deleted_macro_names = macro_handler.delete_file_changes(
            deleted_files, imported_macros, macro_objects
        )

        has_changes = bool(
            imported_template_ids
            or deleted_template_names
            or imported_images
            or deleted_image_names
            or imported_icon_maps
            or deleted_icon_map_names
            or imported_scripts
            or deleted_scripts
            or imported_macros
            or deleted_macro_names
        )

        # Inform user about the changes
        if self.settings.DRY_RUN:
            self.logger.info("Dry run enabled, no changes will be made to Zabbix")
            self.logger.info(
                "Would have imported %s templates, deleted %s templates",
                len(imported_template_ids),
                len(deleted_template_names),
            )
            self.logger.info(
                "Would have imported %s images, deleted %s images",
                len(imported_images),
                len(deleted_image_names),
            )
            self.logger.info(
                "Would have imported %s icon maps, deleted %s icon maps",
                len(imported_icon_maps),
                len(deleted_icon_map_names),
            )
            self.logger.info(
                "Would have imported %s scripts, deleted %s scripts",
                len(imported_scripts),
                len(deleted_scripts),
            )
            self.logger.info(
                "Would have imported %s global macros, deleted %s global macros",
                len(imported_macros),
                len(deleted_macro_names),
            )
        elif has_changes:
            self.logger.info(
                "Imported %s templates, deleted %s templates",
                len(imported_template_ids),
                len(deleted_template_names),
            )
            self.logger.info(
                "Imported %s images, deleted %s images",
                len(imported_images),
                len(deleted_image_names),
            )
            self.logger.info(
                "Imported %s icon maps, deleted %s icon maps",
                len(imported_icon_maps),
                len(deleted_icon_map_names),
            )
            self.logger.info(
                "Imported %s scripts, deleted %s scripts",
                len(imported_scripts),
                len(deleted_scripts),
            )
            self.logger.info(
                "Imported %s global macros, deleted %s global macros",
                len(imported_macros),
                len(deleted_macro_names),
            )
        else:
            self.logger.info("No changes detected, Zabbix is up to date")

        if failed_template_names:
            self.logger.error(
                "Failed to import the following templates: %s",
                ", ".join(failed_template_names),
            )

        # clean local changes
        self._git.clean()
        return has_changes

    def generate_images(self, image_type: str) -> bool:
        """
        Generate icons/backgrounds from Zabbix and save them to the cache
        """
        if not self._git or not self._zabbix:
            raise ValueError(
                "ZabbixCI has not been initialized, call create_zabbix() and create_git() first"
            )

        if not self.settings.REMOTE:
            raise ValueError("Remote repository not set")

        self._git.fetch(self.settings.REMOTE)

        self.logger.info("Generating icons from Zabbix")

        image_handler = ImageHandler(self._zabbix, self.settings)

        if image_type == "background":
            image_handler.generate_backgrounds()
        elif image_type == "icon":
            image_handler.generate_icons()

        if not self._git.is_empty:
            # If the repository is empty, new branches can't be created. But it is
            # safe to push to the default branch
            self._git.switch_branch(self.settings.PUSH_BRANCH)

            # Pull the latest remote state
            try:
                self._git.pull(self.settings.REMOTE)
            except KeyError:
                self.logger.info(
                    "Remote branch does not exist, using state from branch: %s",
                    self.settings.PULL_BRANCH,
                )
                # Remote branch does not exist, we pull the default branch and create a new branch
                self._git.switch_branch(self.settings.PULL_BRANCH)
                self._git.pull(self.settings.REMOTE)

                # Create a new branch
                self._git.switch_branch(self.settings.PUSH_BRANCH)

        # Check if there are any changes to commit
        if not self._git.has_changes and not self._git.ahead_of_remote:
            self.logger.info("No changes detected")
            return False

        self.logger.info("Remote differs from local state, preparing to push")
        change_amount = len(self._git.status())

        # Check if we have any changes to commit. Otherwise, we just push the current state
        if self._git.has_changes:
            # Commit and push the changes
            self._git.add_all()

            if not self.settings.DRY_RUN:
                # Generate commit message
                self._git.commit(f"Generated {image_type}(s) from source files")
                self.logger.info(
                    "Staged changes from generated images committed to %s",
                    self._git.current_branch,
                )
        else:
            self.logger.info("No staged changes, updating remote with current state")

        if not self.settings.DRY_RUN:
            self._git.push(self.settings.REMOTE)
            self.logger.info(
                "Committed %s new changes to %s:%s",
                change_amount,
                self.settings.REMOTE,
                self.settings.PUSH_BRANCH,
            )
        else:
            self.logger.info(
                "Dry run enabled, would have committed %s new changes to %s:%s",
                change_amount,
                self.settings.REMOTE,
                self.settings.PUSH_BRANCH,
            )

        return change_amount > 0
