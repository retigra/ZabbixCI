from utils.zabbix import Zabbix
from utils.git import Git
import logging

import pygit2
from pygit2.enums import ResetMode
import os
from ruamel.yaml import YAML
from io import StringIO


REMOTE = os.getenv("GIT_REMOTE")
CACHE_PATH = os.getenv("CACHE_PATH", "./cache")

if not REMOTE:
    raise ValueError("GIT_REMOTE is not set")

logger = logging.getLogger(__name__)

zabbix = Zabbix(
    "https://zabbix.intra.hedium.nl",
)

# Initialize the git repository
git = Git(CACHE_PATH)
yaml = YAML()


def zabbix_to_file(cache_path=CACHE_PATH):
    """
    Export Zabbix templates to the cache
    """
    templates = zabbix.get_templates()

    logger.info(f"Found {len(templates)} templates in Zabbix")

    # Get the templates
    template_yaml = zabbix.export_template(
        [template["templateid"] for template in templates])

    if logger.level == logging.DEBUG:
        with open("./tests/template.yaml", "w") as file:
            file.write(template_yaml)

    export_yaml = yaml.load(StringIO(template_yaml))

    if not 'templates' in export_yaml['zabbix_export']:
        logger.info("No templates found in Zabbix")

        # Clean the cache
        for file in os.listdir(cache_path):
            if file.endswith(".yaml"):
                os.remove(f"{cache_path}/{file}")

        return

    # Write the templates to the cache
    for template in export_yaml['zabbix_export']['templates']:
        with open(f"{cache_path}/{template['name']}.yaml", "w") as file:
            yaml.dump({
                **template,
                "synchronization_zabbix_version": export_yaml['zabbix_export']['version'],
            }, file)


def push():
    """
    Fetch Zabbix state and commit changes to git remote
    """
    git.switch_branch("development")

    # Reflect current Zabbix state in the cache
    for file in os.listdir(f"{CACHE_PATH}/"):
        if file.endswith(".yaml"):
            os.remove(f"{CACHE_PATH}/{file}")

    zabbix_to_file()

    # Check if there are any changes to commit
    if not git.has_changes:
        logger.info("No changes detected")
        exit()

    logger.info("Changes detected, pushing template updates to git")

    # Commit and push the changes
    git.add_all()
    git.commit("Update templates")
    git.push(REMOTE, pygit2.KeypairFromAgent("git"))

    logger.info("Changes pushed to git")


def pull():
    """
    Pull current state from git remote and update Zabbix
    """
    git.switch_branch("development")

    # Reflect current Zabbix state in the cache
    for file in os.listdir(CACHE_PATH):
        if file.endswith(".yaml"):
            os.remove(f"{CACHE_PATH}/{file}")

    zabbix_to_file()

    # Pull the latest remote state, untracked changes are preserved
    current_revision = git.get_current_revision()
    git.pull(REMOTE, pygit2.KeypairFromAgent("git"))

    # Check for untracked changes, if there are any, we know Zabbix is out of sync
    if git.has_changes:
        logger.info(
            "Detected local file changes, detecting changes for zabbix sync")

    # Save a list of changed files
    changes = git.diff(current_revision)
    files = [patch.delta.new_file.path for patch in changes]

    # Sync the file cache with the desired git state
    git.reset(current_revision, ResetMode.HARD)

    # Import the changed files into Zabbix
    for file in files:
        logger.info(f"Detected change in {file}")

        with open(f"{CACHE_PATH}/{file}", "r") as f:
            template = yaml.load(f)

            if not template:
                continue

            zabbix.import_template(template)
            logger.info(f"Template {template['name']} updated in Zabbix")


if __name__ == "__main__":
    args = os.sys.argv[1:]

    logging.basicConfig(format="%(asctime)s - %(message)s", level=logging.INFO)

    if not args:
        raise ValueError("No arguments provided")

    if args[0] == "push":
        push()

    if args[0] == "pull":
        pull()
