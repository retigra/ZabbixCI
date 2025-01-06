import logging
import os
import timeit

import pygit2
from pygit2.enums import FileStatus, ResetMode
from regex import search
from ruamel.yaml import YAML

from zabbixci.settings import Settings
from zabbixci.utils.git import Git
from zabbixci.utils.template import Template
from zabbixci.utils.zabbix import Zabbix
from zabbixci.zabbixci import cleanup_cache, ignore_template, zabbix_to_file

credentials = pygit2.KeypairFromAgent("git")
GIT_CB = pygit2.RemoteCallbacks(credentials=credentials)

if Settings.INSECURE_SSL_VERIFY:
    GIT_CB.certificate_check = lambda *args, **kwargs: True

logger = logging.getLogger(__name__)
yaml = YAML()

# Initialize the Zabbix API
zabbix = Zabbix(
    url=Settings.ZABBIX_URL,
    user=Settings.ZABBIX_USER,
    password=Settings.ZABBIX_PASSWORD,
    token=Settings.ZABBIX_TOKEN,
    validate_certs=not Settings.INSECURE_SSL_VERIFY,
)


# Initialize the git repository
git = Git(Settings.CACHE_PATH, GIT_CB)


def push():
    """
    Fetch Zabbix state and commit changes to git remote
    """
    git.fetch(Settings.REMOTE, GIT_CB)

    if not git.is_empty:
        # If the repository is empty, new branches can't be created. But it is
        # safe to push to the default branch
        git.switch_branch(Settings.PUSH_BRANCH)

        # Pull the latest remote state
        try:
            git.pull(Settings.REMOTE, GIT_CB)
        except KeyError:
            logger.info(
                f"Remote branch does not exist, using state from branch {Settings.PULL_BRANCH}"
            )
            # Remote branch does not exist, we pull the default branch and create a new branch
            git.switch_branch(Settings.PULL_BRANCH)
            git.pull(Settings.REMOTE, GIT_CB)

            # Create a new branch
            git.switch_branch(Settings.PUSH_BRANCH)

    # Reflect current Zabbix state in the cache
    cleanup_cache()

    zabbix_to_file(zabbix)

    # Check if there are any changes to commit
    if not git.has_changes and not git.ahead_of_remote:
        logger.info("No changes detected")
        exit()

    logger.info("Remote differs from local state, preparing to push")

    # Commit and push the changes
    git.add_all()

    host = os.getenv(
        "ZABBIX_HOST", search("https?://([^/]+)", zabbix.zapi.url).group(1)
    )

    if git.has_changes:
        # Create a commit
        changes = git.diff()
        files = [patch.delta.new_file.path for patch in changes]

        for file in files:
            logger.info(f"Detected change in {file}")

        # Generate commit message
        git.commit(f"Committed Zabbix state from {host}")
        logger.info(f"Staged changes from {host} committed to {git.current_branch}")
    else:
        logger.info("No staged changes, updating remote with current state")

    git.push(Settings.REMOTE, GIT_CB)


def pull():
    """
    Pull current state from git remote and update Zabbix
    """
    git.switch_branch(Settings.PULL_BRANCH)

    # Pull the latest remote state, untracked changes are preserved
    git.pull(Settings.REMOTE, GIT_CB)
    git.reset(
        git._repository.lookup_reference(
            f"refs/remotes/origin/{Settings.PULL_BRANCH}"
        ).target,
        ResetMode.HARD,
    )

    current_revision = git.get_current_revision()

    # Reflect current Zabbix state in the cache
    cleanup_cache()
    zabbix_to_file()

    zabbix_version = zabbix.get_server_version()

    # Check for untracked changes, if there are any, we know Zabbix is out of
    # sync
    if git.has_changes:
        logger.info("Detected local file changes, detecting changes for zabbix sync")

    status = git.status()

    # Get the changed files, we compare the untracked changes with the desired.
    # When we have a new untracked file, that means it was deleted in the desired state.
    files = [
        path
        for path, flags in status.items()
        if flags in [FileStatus.WT_DELETED, FileStatus.WT_MODIFIED]
    ]
    deleted_files = [
        path for path, flags in status.items() if flags == FileStatus.WT_NEW
    ]

    logger.debug(f"Following templates have changed on Git: {files}")
    logger.debug(f"Following templates are deleted from Git {deleted_files}")

    # Sync the file cache with the desired git state
    git.reset(current_revision, ResetMode.HARD)

    templates: list[Template] = []

    # Open the changed files
    for file in files:
        # Check if file is within the desired path
        if not file.startswith(Settings.GIT_PREFIX_PATH):
            continue

        if not file.endswith(".yaml"):
            continue

        template = Template.open(file)

        if not template or not template.is_template:
            continue

        if ignore_template(template.name):
            continue

        if (
            not Settings.IGNORE_VERSION
            and template.zabbix_version.split(".")[0:2]
            != zabbix_version.split(".")[0:2]
        ):
            logger.warning(
                f"Template {template.name}: {template.zabbix_version} must match major Zabbix version {'.'.join(zabbix_version.split('.')[0:2])}"
            )
            continue

        templates.append(template)
        logger.info(f"Detected change in {template.name}")

    if len(templates):
        tic = timeit.default_timer()

        # Group templates by level
        templates = sorted(templates, key=lambda template: template.level(templates))

        toc = timeit.default_timer()
        logger.info("Sorted templates in {:.2f}s".format(toc - tic))

        # Import the templates
        for template in templates:
            logger.info(f"Importing {template.name}, level {template._level}")
            zabbix.import_template(template)

    template_names = []

    # Delete the deleted templates
    for file in deleted_files:
        template = Template.open(file)

        if not template or not template.is_template:
            logger.warning(f"Could not open to be deleted file {file}")
            continue

        if ignore_template(template.name):
            continue

        if template.uuid in [t.uuid for t in templates]:
            logger.debug(
                f"Template {template.name} is being imported under a different name or path, skipping deletion"
            )
            continue

        template_names.append(template.name)
        logger.info(f"Added {template.name} to deletion queue")

    if len(template_names):
        logger.info(f"Deleting {len(template_names)} templates from Zabbix")
        template_ids = [
            t["templateid"] for t in zabbix.get_templates_name(template_names)
        ]

        if len(template_ids):
            zabbix.delete_template(template_ids)

    # clean local changes
    git.clean()
