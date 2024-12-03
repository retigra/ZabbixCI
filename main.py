from utils.zabbix.zabbix import Zabbix
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


# Get the git repository
repository: pygit2.Repository = None

if os.path.exists("./cache"):
    repository = pygit2.Repository("./cache")
else:
    repository = pygit2.init_repository("./cache", initial_head="main")

export_yaml = yaml.load(StringIO(template_yaml), Loader=yaml.FullLoader)

for template in export_yaml['zabbix_export']['templates']:
    with open(f"./cache/{template['name']}.yaml", "w") as file:
        yaml.dump(template, file)

# Commit changes as new commit
index = repository.index
index.add_all()
index.write()
ref = "HEAD"
index.add_all()
index.write()

tree = index.write_tree()

author = pygit2.Signature("Zabbix Configuration", "zabbix@example.com")
committer = pygit2.Signature("Zabbix Configuration", "zabbix@example.com")

parents = []

# Check if repo has a head
if not repository.head_is_unborn:
    parents = [repository.head.target]

remote = repository.remotes['origin']

if not remote:
    remote = repository.remotes.create('origin', REMOTE)

credentials = pygit2.KeypairFromAgent("git")
callbacks = pygit2.RemoteCallbacks(credentials=credentials)

status = repository.status()

if len(status) == 0:
    logger.info("No changes detected")
    exit()

repository.create_commit(
    ref,
    author,
    committer,
    "Updated templates",
    tree,
    parents
)

remote.push(["refs/heads/main"], callbacks=callbacks)
logger.info("Pushed changes to remote")
