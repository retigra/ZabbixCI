import asyncio
import logging
import os
import ssl
import timeit
import urllib.error
from io import StringIO
from urllib.request import Request, urlopen

import pygit2
from pygit2.enums import FileStatus, ResetMode
from regex import search
from ruamel.yaml import YAML

from zabbixci.settings import Settings
from zabbixci.utils.git import Git
from zabbixci.utils.template import Template
from zabbixci.utils.zabbix import Zabbix


class ZabbixCI:
    logger = logging.getLogger(__name__)
    yaml = YAML()

    _settings = None
    _git_cb = None

    _zabbix = None
    _git = None

    _ssl_context = None
    _ssl_valid = False

    def __init__(self, settings=Settings, logger=None):
        self._settings = settings

        if logger:
            self.logger = logger

        self.create_git_callback()
        self.create_git()

    def validate_ssl_cert(self, cert: None, valid: bool, hostname: bytes):
        """
        Callback function for pygit2 RemoteCallbacks object to validate SSL certificates

        :param cert: Certificate object (this is always None in pygit2)
        :param valid: Whether the certificate is valid
        :param hostname: Hostname of the certificate
        """
        hostname_str = hostname.decode("utf-8")

        if valid:
            # If native SSL validation is successful, we can skip the custom check
            return True

        if self._ssl_valid:
            # If the certificate has already been validated, we can skip the check
            return True

        # Check if the certificate matches in SSL context
        # Certificate is not given by pygit2, so we request it ourself
        # by making a request to the hostname with urllib
        try:
            req = Request(
                f"https://{hostname_str}",
                method="GET",
            )
            resp = urlopen(req, context=self._ssl_context)

            self.logger.debug(f"Response from {hostname_str}: {resp.status}")

            self._ssl_valid = True
            return True
        except urllib.error.URLError as e:
            self.logger.error(f"Error validating SSL certificate: {e}")
            return False

    def create_git_callback(self):
        """
        Create a pygit2 RemoteCallbacks object with the appropriate credentials
        Handles both username/password and SSH keypair authentication

        :param settings: Settings object
        """
        if self._settings.GIT_USERNAME and self._settings.GIT_PASSWORD:
            self.logger.info("Using username and password for authentication")
            credentials = pygit2.UserPass(
                self._settings.GIT_USERNAME, self._settings.GIT_PASSWORD
            )
        elif self._settings.GIT_PUBKEY and self._settings.GIT_PRIVKEY:
            self.logger.info("Using SSH keypair for authentication")
            credentials = pygit2.Keypair(
                self._settings.GIT_USERNAME,
                self._settings.GIT_PUBKEY,
                self._settings.GIT_PRIVKEY,
                self._settings.GIT_KEYPASSPHRASE,
            )
        else:
            self.logger.info("Using SSH agent for authentication")
            credentials = pygit2.KeypairFromAgent(self._settings.GIT_USERNAME)

        self._git_cb = pygit2.RemoteCallbacks(credentials=credentials)

        if self._settings.INSECURE_SSL_VERIFY:
            # Accept all certificates
            self._git_cb.certificate_check = lambda cert, valid, hostname: True
        elif self._settings.CA_BUNDLE:
            # Validate certificates with the provided CA bundle
            self._git_cb.certificate_check = self.validate_ssl_cert

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
            self.logger.info("Using username and password for authentication")
            await self._zabbix.zapi.login(
                user=self._settings.ZABBIX_USER, password=self._settings.ZABBIX_PASSWORD
            )
        elif self._settings.ZABBIX_TOKEN:
            self.logger.info("Using token for authentication")
            await self._zabbix.zapi.login(token=self._settings.ZABBIX_TOKEN)

    def create_git(self):
        """
        Create a Git object with the appropriate credentials
        """
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
        await self.zabbix_to_file()

        # Check if there are any changes to commit
        if not self._git.has_changes and not self._git.ahead_of_remote:
            self.logger.info("No changes detected")
            return

        self.logger.info("Remote differs from local state, preparing to push")

        # Commit and push the changes
        self._git.add_all()

        host = os.getenv(
            "ZABBIX_HOST", search("https?://([^/]+)", self._zabbix.zapi.url).group(1)
        )

        if self._git.has_changes:
            # Create a commit
            changes = self._git.diff()
            files = [patch.delta.new_file.path for patch in changes]

            for file in files:
                self.logger.info(f"Detected change in {file}")

            # Generate commit message
            self._git.commit(f"Committed Zabbix state from {host}")
            self.logger.info(
                f"Staged changes from {host} committed to {self._git.current_branch}"
            )
        else:
            self.logger.info("No staged changes, updating remote with current state")

        if not self._settings.DRY_RUN:
            self._git.push(Settings.REMOTE, self._git_cb)

    async def pull(self):
        """
        Pull current state from git remote and update Zabbix
        """
        self._git.switch_branch(Settings.PULL_BRANCH)

        # Pull the latest remote state, untracked changes are preserved
        self._git.pull(Settings.REMOTE, self._git_cb)
        self._git.reset(
            self._git._repository.lookup_reference(
                f"refs/remotes/origin/{Settings.PULL_BRANCH}"
            ).target,
            ResetMode.HARD,
        )

        current_revision = self._git.get_current_revision()

        # Reflect current Zabbix state in the cache
        self.cleanup_cache()
        await self.zabbix_to_file()

        zabbix_version = self._zabbix.get_server_version()

        # Check for untracked changes, if there are any, we know Zabbix is out of
        # sync
        if self._git.has_changes:
            self.logger.info(
                "Detected local file changes, detecting changes for zabbix sync"
            )

        status = self._git.status()

        # Get the changed files, we compare the untracked changes with the desired.
        # When we have a new untracked file, that means it was deleted in the desired state.
        files: list[str] = [
            path
            for path, flags in status.items()
            if flags in [FileStatus.WT_DELETED, FileStatus.WT_MODIFIED]
        ]
        deleted_files: list[str] = [
            path for path, flags in status.items() if flags == FileStatus.WT_NEW
        ]

        self.logger.debug(f"Following templates have changed on Git: {files}")
        self.logger.debug(f"Following templates are deleted from Git {deleted_files}")

        # Sync the file cache with the desired git state
        self._git.reset(current_revision, ResetMode.HARD)

        templates: list[Template] = []

        # Open the changed files
        for file in files:
            if not file.endswith(".yaml"):
                continue

            # Check if file is within the desired path
            if not file.startswith(Settings.TEMPLATE_PREFIX_PATH):
                self.logger.debug(f"Skipping .yaml file {file} outside of prefix path")
                continue

            template = Template.open(file)

            if not template or not template.is_template:
                self.logger.warning(f"Could load file {file} as a template")
                continue

            if self.ignore_template(template.name):
                continue

            if (
                not Settings.IGNORE_TEMPLATE_VERSION
                and template.zabbix_version.split(".")[0:2]
                != zabbix_version.split(".")[0:2]
            ):
                self.logger.warning(
                    f"Template {template.name}: {template.zabbix_version} must match major Zabbix version {'.'.join(zabbix_version.split('.')[0:2])}"
                )
                continue

            templates.append(template)
            self.logger.info(f"Detected change in {template.name}")

        if len(templates):
            tic = timeit.default_timer()

            # Group templates by level
            templates = sorted(
                templates, key=lambda template: template.level(templates)
            )

            toc = timeit.default_timer()
            self.logger.info("Sorted templates in {:.2f}s".format(toc - tic))

            failed_templates = []

            # Import the templates
            for template in templates:
                self.logger.info(f"Importing {template.name}, level {template._level}")

                if not self._settings.DRY_RUN:
                    try:
                        self._zabbix.import_template(template)
                    except Exception as e:
                        self.logger.warning(
                            f"Error importing template {template.name}, will try to import later"
                        )
                        self.logger.debug(f"Error details: {e}")
                        failed_templates.append(template.name)

            if len(failed_templates):
                for template in failed_templates:
                    try:
                        self._zabbix.import_template(template)
                    except Exception as e:
                        self.logger.error(f"Error importing template {template}: {e}")

        deletion_queue = []
        imported_template_ids = []

        for t in templates:
            imported_template_ids.extend(t.template_ids)

        # Delete the deleted templates
        for file in deleted_files:
            template = Template.open(file)

            if not template or not template.is_template:
                self.logger.warning(f"Could not open to be deleted file {file}")
                continue

            if self.ignore_template(template.name):
                continue

            if template.uuid in imported_template_ids:
                self.logger.debug(
                    f"Template {template.name} is being imported under a different name or path, skipping deletion"
                )
                continue

            deletion_queue.append(template.name)
            self.logger.info(f"Added {template.name} to deletion queue")

        if len(deletion_queue):
            self.logger.info(f"Deleting {len(deletion_queue)} templates from Zabbix")
            template_ids = [
                t["templateid"] for t in self._zabbix.get_templates_name(deletion_queue)
            ]

            if len(template_ids):
                if not self._settings.DRY_RUN:
                    self._zabbix.delete_template(template_ids)

        # clean local changes
        self._git.clean()

    async def zabbix_export(self, templates: list[str]):
        batches = [
            templates[i : i + Settings.BATCH_SIZE]
            for i in range(0, len(templates), Settings.BATCH_SIZE)
        ]

        failed_exports = []

        for index, batch in enumerate(batches):
            self.logger.info(f"Processing batch {index + 1}/{len(batches)}")
            coros = []
            for t in batch:
                coros.append(self._zabbix.export_template_async([t["templateid"]]))

            responses = await asyncio.gather(*coros, return_exceptions=True)

            for index, response in enumerate(responses):
                if isinstance(response, Exception):
                    self.logger.error(f"Error exporting template: {response}")

                    # Retry the export
                    failed_exports.append(batch[index])
                    continue

                export_yaml = self.yaml.load(StringIO(response["result"]))

                if not "templates" in export_yaml["zabbix_export"]:
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

    async def zabbix_to_file(self) -> None:
        """
        Export Zabbix templates to the cache
        """
        templates = self._zabbix.get_templates([Settings.ROOT_TEMPLATE_GROUP])

        self.logger.info(f"Found {len(templates)} templates in Zabbix")
        self.logger.debug(f"Found Zabbix templates: {[t['name'] for t in templates]}")

        await self.zabbix_export(templates)

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

        if full:
            os.rmdir(Settings.CACHE_PATH)
            cls.logger.info("Cache directory cleared")

    @classmethod
    def ignore_template(cls, template_name: str) -> bool:
        """
        Returns true if template should be ignored because of the blacklist or whitelist
        """
        if template_name in Settings.TEMPLATE_BLACKLIST:
            cls.logger.debug(f"Skipping blacklisted template {template_name}")
            return True

        if (
            len(Settings.TEMPLATE_WHITELIST)
            and template_name not in Settings.TEMPLATE_WHITELIST
        ):
            cls.logger.debug(f"Skipping non whitelisted template {template_name}")
            return True

        return False
