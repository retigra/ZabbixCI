![ZabbixCI cog logo](logo.png "ZabbixCI logo")

# ZabbixCI

ZabbixCI is a tool that adds continuous integration to Zabbix configurations,
allowing you to synchronize Zabbix configurations with a Git repository. By
using the Zabbix API, ZabbixCI can create, update, and delete templates across
multiple Zabbix servers.

## Installation

ZabbixCI is available on PyPI and can be installed using pip:

```bash
pip install zabbixci
```

and then you can use the `zabbixci` command.

## Configuration

ZabbixCI requires parameters to be set as command line arguments or environment
variables. The following parameters are required:

```bash
# Zabbix API Options
ZABBIX_URL="https://zabbix.example..com"
# ZABBIX_USER="Admin"
# ZABBIX_PASSWORD="zabbix"
ZABBIX_TOKEN=""

# Git Options
GIT_REMOTE="git@github.com:retigra/zabbixci-configuration.git"
GIT_PREFIX_PATH="templates"

# ZabbixCI Options
# Template Group to synchronize 
PARENT_GROUP="Templates"

# Branches to use
PULL_BRANCH="main"
PUSH_BRANCH="main"

# Optional whitelist and blacklist matching templates names
WHITELIST=""
BLACKLIST=""
```

## Usage

The `zabbixci` command can be used to synchronize Zabbix templates with a Git
repository. The command will pull templates from the Git repository and push
them to the Zabbix server. The command will also delete templates that are not
present in the Git repository.

```bash
zabbixci --debug --dotenv .env pull

zabbixci --debug --dotenv .env push

zabbixci help
```

# Contributing

Contributions are welcome! Please take a look at the following guidelines:

- Commit messages should follow the [Gitmoji](https://gitmoji.dev/) convention.
- Code should be formatted using [autopep8](https://pypi.org/project/autopep8/).

# License

to be defined
