from utils.zabbix import Zabbix
from utils.git import Git
import logging

import pygit2
import os
from ruamel.yaml import YAML
from io import StringIO


REMOTE = os.getenv("GIT_REMOTE")

if not REMOTE:
    raise ValueError("GIT_REMOTE is not set")

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

zabbix = Zabbix(
    "https://zabbix.intra.hedium.nl",
)

# Initialize the git repository
git = Git()

yaml = YAML()


def push():
    templates = zabbix.get_templates()

    # Get the templates
    template_yaml = zabbix.export_template(
        [template["templateid"] for template in templates])

    with open("./tests/template.yaml", "w") as file:
        file.write(template_yaml)

    export_yaml = yaml.load(StringIO(template_yaml))

    # Write the templates to the cache
    for template in export_yaml['zabbix_export']['templates']:
        with open(f"./cache/{template['name']}.yaml", "w") as file:
            yaml.dump({
                **template,
                "synchronization_zabbix_version": export_yaml['zabbix_export']['version'],
            }, file)

    git.switch_branch("development")

    if not git.has_changes:
        logger.info("No changes detected")
        exit()

    git.add_all()
    git.commit("Update templates")
    git.push(REMOTE, pygit2.KeypairFromAgent("git"))

    logger.info("Changes pushed to git")


def pull():
    git.switch_branch("development")

    current_revision = git.get_current_revision()
    git.pull(REMOTE, pygit2.KeypairFromAgent("git"))

    if current_revision == git.get_current_revision():
        logger.info("No changes detected")
        exit()

    changes = git.diff(current_revision)

    for patch in changes:
        file = patch.delta.new_file.path

        with open(f"./cache/{file}", "r") as f:
            template = yaml.load(f)

            if not template:
                continue

            zabbix.import_template(template)
            logger.info(f"Template {template['name']} created")


if __name__ == "__main__":
    args = os.sys.argv[1:]

    if not args:
        raise ValueError("No arguments provided")

    if args[0] == "push":
        push()

    if args[0] == "pull":
        pull()
