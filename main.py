from utils.zabbix import Zabbix
from utils.git import Git
import logging

import pygit2
import os
import yaml
from io import StringIO

REMOTE = os.getenv("GIT_REMOTE")

if not REMOTE:
    raise ValueError("GIT_REMOTE is not set")

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

zabbix = Zabbix(
    "https://zabbix.intra.hedium.nl",
)

templates = zabbix.get_templates()

# Get the templates
template_yaml = zabbix.export_template(
    [template["templateid"] for template in templates])


export_yaml = yaml.load(StringIO(template_yaml), Loader=yaml.FullLoader)

# Initialize the git repository
git = Git()

# Write the templates to the cache
for template in export_yaml['zabbix_export']['templates']:
    with open(f"./cache/{template['name']}.yaml", "w") as file:
        yaml.dump(template, file)

if not git.has_changes:
    logger.info("No changes detected")
    exit()

git.add_all()
git.commit("Update templates")
git.push(REMOTE, pygit2.KeypairFromAgent("git"))

logger.info("Changes pushed to git")
