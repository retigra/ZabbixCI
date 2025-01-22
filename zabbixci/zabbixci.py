import asyncio
import logging
import os
import ssl
from datetime import datetime, timezone
from io import StringIO

from pygit2.enums import FileStatus, ResetMode
from regex import search
from ruamel.yaml import YAML

from zabbixci.settings import Settings
from zabbixci.utils.git import Git, GitCredentials
from zabbixci.utils.handers.image import ImageHandler
from zabbixci.utils.handers.template import TemplateHandler
from zabbixci.utils.services import Template
from zabbixci.utils.services.image import Image
from zabbixci.utils.zabbix import Zabbix


class ZabbixCI:
    logger = logging.getLogger(__name__)
    yaml = YAML()

    _zabbix = None
    _git = None
    _git_cb = None

    _ssl_context = None

    def __init__(self, settings=Settings, logger=None):
        self._settings = settings

        if logger:
            self.logger = logger

        self.create_git(GitCredentials().create_git_callback())

    async def create_zabbix(self):
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

        if self._zabbix.zapi.version < 7.0:
            self.logger.error(
                f"Zabbix server version {self._zabbix.zapi.version} is not supported (7.0+ required)"
            )
            raise SystemExit(1)

    def create_git(self, git_cb):
        """
        Create a Git object with the appropriate credentials
        """
        self._git_cb = git_cb
        self._git = Git(self._settings.CACHE_PATH, self._git_cb)

    async def push(self):
        """
        Fetch Zabbix state and commit changes to git remote
        """
        self._git.fetch(Settings.REMOTE, self._git_cb)

        if not self._git.is_empty:
            # If the repository is empty, new branches can't be created. But it is
            # safe to push to the default branch
            self._git.switch_branch(Settings.PUSH_BRANCH)

            # Pull the latest remote state
            try:
                self._git.pull(Settings.REMOTE, self._git_cb)
            except KeyError:
                self.logger.info(
                    f"Remote branch does not exist, using state from branch {Settings.PULL_BRANCH}"
                )
                # Remote branch does not exist, we pull the default branch and create a new branch
                self._git.switch_branch(Settings.PULL_BRANCH)
                self._git.pull(Settings.REMOTE, self._git_cb)

                # Create a new branch
                self._git.switch_branch(Settings.PUSH_BRANCH)

        # Reflect current Zabbix state in the cache
        self.cleanup_cache()
        templates = await self.templates_to_cache()

        self.images_to_cache()

        # Check if there are any changes to commit
        if not self._git.has_changes and not self._git.ahead_of_remote:
            self.logger.info("No changes detected")
            return False

        self.logger.info("Remote differs from local state, preparing to push")
        change_amount = len(self._git.status())

        # Check if we have any changes to commit. Otherwise, we just push the current state
        if self._git.has_changes:
            # Create a commit
            changes = self._git.status()

            host = os.getenv(
                "ZABBIX_HOST",
                search("https?://([^/]+)", self._zabbix.zapi.url).group(1),
            )

            change_amount = len(changes)

            for file, status in changes.items():
                if status == FileStatus.WT_DELETED:
                    self.logger.info(f"Detected deletion of {file}")
                    continue

                self.logger.info(f"Detected change in {file}")

                if not file.endswith(".yaml"):
                    # TODO create proper split of images and templates
                    continue

                template = Template.open(file)

                if Settings.VENDOR and not template.vendor:
                    set_vendor = Settings.VENDOR
                    template.set_vendor(set_vendor)
                    self.logger.debug(f"Setting vendor to {set_vendor}")

                if Settings.SET_VERSION:
                    new_version = datetime.now(timezone.utc).strftime("%Y.%m.%d %H:%M")
                    template.set_version(new_version)
                    self.logger.debug(f"Setting version to {new_version}")

                if (template.new_version or template.new_vendor) and (
                    template.vendor and template.version
                ):
                    template.save()

                    if not Settings.DRY_RUN:
                        self.logger.debug(
                            f"Updating template metadata for {template.name}"
                        )
                        self._zabbix.set_template(
                            next(
                                filter(lambda t: t["host"] == template.name, templates)
                            )["templateid"],
                            template.updated_items,
                        )

            # Commit and push the changes
            self._git.add_all()

            if not Settings.DRY_RUN:
                # Generate commit message
                self._git.commit(f"Committed Zabbix state from {host}")
                self.logger.info(
                    f"Staged changes from {host} committed to {self._git.current_branch}"
                )
        else:
            self.logger.info("No staged changes, updating remote with current state")

        if not self._settings.DRY_RUN:
            self._git.push(Settings.REMOTE, self._git_cb)
            self.logger.info(
                f"Committed {change_amount} new changes to {Settings.REMOTE}:{Settings.PUSH_BRANCH}"
            )
        else:
            self.logger.info(
                f"Dry run enabled, would have committed {change_amount} new changes to {Settings.REMOTE}:{Settings.PUSH_BRANCH}"
            )

        return change_amount > 0

    async def pull(self):
        """
        Pull current state from git remote and update Zabbix
        """
        self._git.switch_branch(Settings.PULL_BRANCH)

        # Pull the latest remote state, untracked changes are preserved
        self._git.pull(Settings.REMOTE, self._git_cb)
        self._git.reset(
            self._git.lookup_reference(
                f"refs/remotes/origin/{Settings.PULL_BRANCH}"
            ).target,
            ResetMode.HARD,
        )

        current_revision = self._git.get_current_revision()

        # Reflect current Zabbix state in the cache
        self.cleanup_cache()
        template_objects = await self.templates_to_cache()
        image_objects = self.images_to_cache()

        # Check if there are any changes to commit
        if self._git.has_changes:
            self.logger.info("Zabbix state is out of sync, syncing")

        status = self._git.status()

        # Get the changed files, we compare the untracked changes with the desired.
        # When we have a new untracked file, that means it was deleted in the desired state.
        changed_files: list[str] = [
            path
            for path, flags in status.items()
            if flags in [FileStatus.WT_DELETED, FileStatus.WT_MODIFIED]
        ]
        deleted_files: list[str] = [
            path for path, flags in status.items() if flags == FileStatus.WT_NEW
        ]

        self.logger.debug(f"Following files have changed on Git: {changed_files}")
        self.logger.debug(f"Following files are deleted from Git {deleted_files}")

        # Sync the file cache with the desired git state
        self._git.reset(current_revision, ResetMode.HARD)

        template_handler = TemplateHandler(self._zabbix)
        imported_template_ids = template_handler.import_file_changes(changed_files)
        deleted_template_names = template_handler.delete_file_changes(
            deleted_files, imported_template_ids, template_objects
        )

        image_handler = ImageHandler(self._zabbix)
        imported_images = image_handler.import_file_changes(
            changed_files, image_objects
        )

        # Inform user about the changes
        if Settings.DRY_RUN:
            self.logger.info(
                f"Dry run enabled, no changes will be made to Zabbix. Would have imported {len(imported_template_ids)} templates and deleted {len(deleted_template_names)} templates. Would have imported {len(imported_images)} images"
            )
        else:
            if len(deleted_template_names) == 0 and len(imported_template_ids) == 0:
                self.logger.info("No changes detected, Zabbix is up to date")
            else:
                self.logger.info(
                    f"Zabbix state has been synchronized, imported {len(imported_template_ids)} templates and deleted {len(deleted_template_names)} templates. Imported {len(imported_images)} images"
                )

        # clean local changes
        self._git.clean()
        return len(imported_template_ids) > 0 or len(deleted_template_names) > 0

    async def zabbix_export(self, templates: list[dict]):
        batches = [
            templates[i : i + Settings.BATCH_SIZE]
            for i in range(0, len(templates), Settings.BATCH_SIZE)
        ]

        failed_exports = []

        for batchIndex, batch in enumerate(batches):
            self.logger.info(f"Processing batch {batchIndex + 1}/{len(batches)}")
            coros = []
            for t in batch:
                coros.append(self._zabbix.export_template_async([t["templateid"]]))

            responses = await asyncio.gather(*coros, return_exceptions=True)

            for index, response in enumerate(responses):
                if isinstance(response, BaseException):
                    self.logger.error(f"Error exporting template: {response}")

                    # Retry the export
                    failed_exports.append(batch[index])
                    continue

                export_yaml = self.yaml.load(StringIO(response["result"]))

                if "templates" not in export_yaml["zabbix_export"]:
                    self.logger.info("No templates found in Zabbix")
                    return

                zabbix_template = Template.from_zabbix(export_yaml["zabbix_export"])

                if self.ignore_template(zabbix_template.name):
                    continue

                zabbix_template.save()
                self.logger.info(f"Exported Zabbix template {zabbix_template.name}")

        if len(failed_exports):
            self.logger.warning(
                f"Failed to export {len(failed_exports)} templates, retrying"
            )
            await self.zabbix_export(failed_exports)

    async def templates_to_cache(self) -> list[dict]:
        """
        Export Zabbix templates to the cache
        """
        if Settings.get_template_whitelist():
            templates = self._zabbix.get_templates_filtered(
                [Settings.ROOT_TEMPLATE_GROUP], Settings.get_template_whitelist()
            )
        else:
            templates = self._zabbix.get_templates([Settings.ROOT_TEMPLATE_GROUP])

        self.logger.info(f"Found {len(templates)} templates in Zabbix")
        self.logger.debug(f"Found Zabbix templates: {[t['host'] for t in templates]}")

        await self.zabbix_export(templates)
        return templates

    def images_to_cache(self) -> list[str]:
        """
        Export Zabbix images to the cache
        """
        images = self._zabbix.get_images()

        self.logger.info(f"Found {len(images)} images in Zabbix")

        for image in images:
            image_object = Image.from_zabbix(image)
            image_object.save(Settings.IMAGE_PREFIX_PATH)

        return images

    @classmethod
    def cleanup_cache(cls, full: bool = False) -> None:
        """
        Clean all .yaml (template) files from the cache directory

        If full is True, also remove the .git directory and all other files
        """
        for root, dirs, files in os.walk(
            f"{Settings.CACHE_PATH}/{Settings.TEMPLATE_PREFIX_PATH}", topdown=False
        ):
            if f"{Settings.CACHE_PATH}/.git" in root and not full:
                continue

            for name in files:
                if name.endswith(".yaml") or full:
                    os.remove(os.path.join(root, name))

            for name in dirs:
                if name == ".git" and root == Settings.CACHE_PATH and not full:
                    continue

                # Remove empty directories
                if not os.listdir(os.path.join(root, name)):
                    os.rmdir(os.path.join(root, name))

        for root, dirs, files in os.walk(
            f"{Settings.CACHE_PATH}/{Settings.IMAGE_PREFIX_PATH}", topdown=False
        ):
            if f"{Settings.CACHE_PATH}/.git" in root and not full:
                continue

            for name in files:
                if name.endswith(".png") or full:
                    os.remove(os.path.join(root, name))

            for name in dirs:
                if name == ".git" and root == Settings.CACHE_PATH and not full:
                    continue

                # Remove empty directories
                if not os.listdir(os.path.join(root, name)):
                    os.rmdir(os.path.join(root, name))

        if full:
            os.rmdir(Settings.CACHE_PATH)
            cls.logger.info("Cache directory cleared")

    @classmethod
    def ignore_template(cls, template_name: str) -> bool:
        """
        Returns true if template should be ignored because of the blacklist or whitelist
        """
        if template_name in Settings.get_template_blacklist():
            cls.logger.debug(f"Skipping blacklisted template {template_name}")
            return True

        if (
            len(Settings.get_template_whitelist())
            and template_name not in Settings.get_template_whitelist()
        ):
            cls.logger.debug(f"Skipping non whitelisted template {template_name}")
            return True

        return False
