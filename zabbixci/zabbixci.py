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
from zabbixci.handlers.synchronization.icon_map_synchronization import IconMapHandler
from zabbixci.handlers.synchronization.image_synchronization import ImageHandler
from zabbixci.handlers.synchronization.template_synchronization import TemplateHandler
from zabbixci.settings import Settings
from zabbixci.zabbix import Zabbix


class ZabbixCI:
    logger = logging.getLogger(__name__)
    yaml = YAML()

    _zabbix: Zabbix | None = None
    _git: Git | None = None

    _ssl_context = None

    def __init__(self, settings=Settings, logger=None):
        self._settings = settings

        if logger:
            self.logger = logger

    async def create_zabbix(self) -> None:
        """
        Create a Zabbix object with the appropriate credentials
        """
        # Construct the SSL context if a CA bundle is provided

        if Settings.CA_BUNDLE:
            self._ssl_context = ssl.create_default_context()
            self._ssl_context.load_verify_locations(Settings.CA_BUNDLE)

        self._zabbix = Zabbix(
            url=self._settings.ZABBIX_URL,
            validate_certs=not self._settings.INSECURE_SSL_VERIFY,
            ssl_context=self._ssl_context,
        )

        if self._settings.ZABBIX_USER and self._settings.ZABBIX_PASSWORD:
            self.logger.debug("Using username and password for Zabbix authentication")
            await self._zabbix.zapi.login(
                user=self._settings.ZABBIX_USER, password=self._settings.ZABBIX_PASSWORD
            )
        elif self._settings.ZABBIX_TOKEN:
            self.logger.debug("Using token for Zabbix authentication")
            await self._zabbix.zapi.login(token=self._settings.ZABBIX_TOKEN)

        if self._zabbix.zapi.version < 6.0:
            self.logger.error(
                f"Zabbix server version {self._zabbix.zapi.version} is not supported (7.0+ required)"
            )
            raise SystemExit(1)

    def create_git(self, git_cb=None) -> None:
        """
        Create a Git object with the appropriate credentials
        """
        if git_cb is None:
            git_cb = GitCredentials().create_git_callback()

        self._git = Git(self._settings.CACHE_PATH, git_cb)

    async def push(self) -> bool:
        """
        Fetch Zabbix state and commit changes to git remote
        """
        if not self._git or not self._zabbix:
            raise ValueError(
                "ZabbixCI has not been initialized, call create_zabbix() and create_git() first"
            )

        if not Settings.REMOTE:
            raise ValueError("Remote repository not set")

        self._git.fetch(Settings.REMOTE)

        if not self._git.is_empty:
            # If the repository is empty, new branches can't be created. But it is
            # safe to push to the default branch
            self._git.switch_branch(Settings.PUSH_BRANCH)

            # Pull the latest remote state
            try:
                self._git.pull(Settings.REMOTE)
            except KeyError:
                self.logger.info(
                    f"Remote branch does not exist, using state from branch: {Settings.PULL_BRANCH}"
                )
                # Remote branch does not exist, we pull the default branch and create a new branch
                self._git.switch_branch(Settings.PULL_BRANCH)
                self._git.pull(Settings.REMOTE)

                # Create a new branch
                self._git.switch_branch(Settings.PUSH_BRANCH)

        # Reflect current Zabbix state in the cache
        Cleanup.cleanup_cache()

        template_handler = TemplateHandler(self._zabbix)
        image_handler = ImageHandler(self._zabbix)
        icon_map_handler = IconMapHandler(self._zabbix)

        template_objects = await template_handler.templates_to_cache()
        image_objects = image_handler.images_to_cache()
        icon_map_handler.icon_map_to_cache(image_objects)

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
                file = f"{Settings.CACHE_PATH}/{relative_path}"

                if status == FileStatus.WT_DELETED:
                    self.logger.info(f"Detected deletion of: {file}")
                    continue

                self.logger.info(f"Detected change in: {file}")

                if not template_handler.read_validation(file):
                    continue

                template = Template.open(file)

                if (
                    Settings.VENDOR
                    and not template.vendor
                    and self._zabbix.api_version >= 7.0
                ):
                    set_vendor = Settings.VENDOR
                    template.set_vendor(set_vendor)
                    self.logger.debug(f"Setting vendor to: {set_vendor}")

                if Settings.SET_VERSION and self._zabbix.api_version >= 7.0:
                    new_version = datetime.now(timezone.utc).strftime("%Y.%m.%d %H:%M")
                    template.set_version(new_version)
                    self.logger.debug(f"Setting version to: {new_version}")

                if (template.new_version or template.new_vendor) and (
                    template.vendor and template.version
                ):
                    template.save()

                    if not Settings.DRY_RUN:
                        self.logger.debug(
                            f"Updating template metadata for: {template.name}"
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

            # Commit and push the changes
            self._git.add_all()

            if not Settings.DRY_RUN:
                # Generate commit message
                self._git.commit(
                    Settings.GIT_COMMIT_MESSAGE or f"Committed Zabbix state from {host}"
                )
                self.logger.info(
                    f"Staged changes from {host} committed to {self._git.current_branch}"
                )
        else:
            self.logger.info("No staged changes, updating remote with current state")

        if not self._settings.DRY_RUN:
            self._git.push(Settings.REMOTE)
            self.logger.info(
                f"Committed {change_amount} new changes to {Settings.REMOTE}:{Settings.PUSH_BRANCH}"
            )
        else:
            self.logger.info(
                f"Dry run enabled, would have committed {change_amount} new changes to {Settings.REMOTE}:{Settings.PUSH_BRANCH}"
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

        if not Settings.REMOTE:
            raise ValueError("Remote repository not set")

        self._git.switch_branch(Settings.PULL_BRANCH)

        # Pull the latest remote state, untracked changes are preserved
        self._git.pull(Settings.REMOTE)

        self._git.reset(
            self._git.lookup_reference(
                f"refs/remotes/origin/{Settings.PULL_BRANCH}"
            ).target,
            ResetMode.HARD,
        )

        current_revision = self._git.get_current_revision()

        # Reflect current Zabbix state in the cache
        Cleanup.cleanup_cache()

        template_handler = TemplateHandler(self._zabbix)
        image_handler = ImageHandler(self._zabbix)
        icon_map_handler = IconMapHandler(self._zabbix)

        template_objects = await template_handler.templates_to_cache()
        image_objects = image_handler.images_to_cache()
        icon_map_objects = icon_map_handler.icon_map_to_cache(image_objects)

        # Check if there are any changes to commit
        if self._git.has_changes:
            self.logger.info("Zabbix state is out of sync, syncing")

        status = self._git.status()

        # Get the changed files, we compare the untracked changes with the desired.
        # When we have a new untracked file, that means it was deleted in the desired state.
        changed_files: list[str] = [
            f"{Settings.CACHE_PATH}/{path}"
            for path, flags in status.items()
            if flags in [FileStatus.WT_DELETED, FileStatus.WT_MODIFIED]
        ]
        deleted_files: list[str] = [
            f"{Settings.CACHE_PATH}/{path}"
            for path, flags in status.items()
            if flags == FileStatus.WT_NEW
        ]

        self.logger.debug(f"Following files have changed on Git: {changed_files}")
        self.logger.debug(f"Following files are deleted from Git: {deleted_files}")

        diff = self._git.diff()
        Git.print_diff(diff, invert=True)

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

        has_changes = bool(
            imported_template_ids
            or deleted_template_names
            or imported_images
            or deleted_image_names
            or imported_icon_maps
            or deleted_icon_map_names
        )

        # Inform user about the changes
        if Settings.DRY_RUN:
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
        else:
            if has_changes:
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
            else:
                self.logger.info("No changes detected, Zabbix is up to date")

        if failed_template_names:
            self.logger.error(
                "Failed to import the following templates: "
                f"{', '.join(failed_template_names)}"
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

        if not Settings.REMOTE:
            raise ValueError("Remote repository not set")

        self._git.fetch(Settings.REMOTE)

        self.logger.info("Generating icons from Zabbix")

        image_handler = ImageHandler(self._zabbix)

        if image_type == "background":
            image_handler.generate_backgrounds()
        elif image_type == "icon":
            image_handler.generate_icons()

        if not self._git.is_empty:
            # If the repository is empty, new branches can't be created. But it is
            # safe to push to the default branch
            self._git.switch_branch(Settings.PUSH_BRANCH)

            # Pull the latest remote state
            try:
                self._git.pull(Settings.REMOTE)
            except KeyError:
                self.logger.info(
                    f"Remote branch does not exist, using state from branch: {Settings.PULL_BRANCH}"
                )
                # Remote branch does not exist, we pull the default branch and create a new branch
                self._git.switch_branch(Settings.PULL_BRANCH)
                self._git.pull(Settings.REMOTE)

                # Create a new branch
                self._git.switch_branch(Settings.PUSH_BRANCH)

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

            if not Settings.DRY_RUN:
                # Generate commit message
                self._git.commit(f"Generated {image_type}(s) from source files")
                self.logger.info(
                    f"Staged changes from generated images committed to {self._git.current_branch}"
                )
        else:
            self.logger.info("No staged changes, updating remote with current state")

        if not self._settings.DRY_RUN:
            self._git.push(Settings.REMOTE)
            self.logger.info(
                f"Committed {change_amount} new changes to {Settings.REMOTE}:{Settings.PUSH_BRANCH}"
            )
        else:
            self.logger.info(
                f"Dry run enabled, would have committed {change_amount} new changes to {Settings.REMOTE}:{Settings.PUSH_BRANCH}"
            )

        return change_amount > 0
