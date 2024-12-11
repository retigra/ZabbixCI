from utils.zabbix import Zabbix
from utils.git import Git
import logging

import pygit2
from pygit2.enums import ResetMode
import os
from ruamel.yaml import YAML
from io import StringIO


REMOTE = os.getenv("GIT_REMOTE")

if not REMOTE:
    raise ValueError("GIT_REMOTE is not set")

logger = logging.getLogger(__name__)

zabbix = Zabbix(
    "https://zabbix.intra.hedium.nl",
)

# Initialize the git repository
git = Git()
yaml = YAML()


def zabbix_to_file():
    templates = zabbix.get_templates()

    logger.info(f"Found {len(templates)} templates in Zabbix")

    # Get the templates
    template_yaml = zabbix.export_template(
        [template["templateid"] for template in templates])

    with open("./tests/template.yaml", "w") as file:
        file.write(template_yaml)

    export_yaml = yaml.load(StringIO(template_yaml))

    if not 'templates' in export_yaml['zabbix_export']:
        logger.info("No templates found in Zabbix")

        # Clean the cache
        for file in os.listdir("./cache"):
            if file.endswith(".yaml"):
                os.remove(f"./cache/{file}")

        return

    # Write the templates to the cache
    for template in export_yaml['zabbix_export']['templates']:
        with open(f"./cache/{template['name']}.yaml", "w") as file:
            yaml.dump({
                **template,
                "synchronization_zabbix_version": export_yaml['zabbix_export']['version'],
            }, file)


def push():
    zabbix_to_file()

    git.switch_branch("development")

    if not git.has_changes:
        logger.info("No changes detected")
        exit()

    logger.info("Changes detected, pushing template updates to git")

    git.add_all()
    git.commit("Update templates")
    git.push(REMOTE, pygit2.KeypairFromAgent("git"))

    logger.info("Changes pushed to git")


def pull():
    git.switch_branch("development")

    # Clean the cache
    for file in os.listdir("./cache"):
        if file.endswith(".yaml"):
            os.remove(f"./cache/{file}")

    zabbix_to_file()

    current_revision = git.get_current_revision()
    git.pull(REMOTE, pygit2.KeypairFromAgent("git"))

    # Restore to the desired revision
    if git.has_changes:
        logger.info(
            "Detected local file changes, detecting changes for zabbix sync")

    # Get the files that are different in current revision
    changes = git.diff(current_revision)

    files = [patch.delta.new_file.path for patch in changes]

    git.repository.reset(current_revision, ResetMode.HARD)

    # Patch Zabbix with the changes
    for file in files:
        logger.info(f"Detected change in {file}")

        with open(f"./cache/{file}", "r") as f:
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
