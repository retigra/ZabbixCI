# ZabbixCI - Getting Started

ZabbixCI is a tool that adds continuous integration to Zabbix configurations,
allowing you to synchronize Zabbix configurations with a Git repository. By
using the Zabbix API, ZabbixCI can create, update, and delete templates across
multiple Zabbix servers.

## Installation

ZabbixCI is available on [PyPI](https://pypi.org/project/zabbixci/) and can be
installed using pip:

```bash
pip install zabbixci
```

Alternatively, you can use a container image to run ZabbixCI, see the available
[container images](https://github.com/retigra/ZabbixCI/pkgs/container/zabbixci).
See the [Containerized Deployment](Containerized.md) documentation for more

## Configuration

ZabbixCI requires parameters to be set as command line arguments, a yaml
configuration or as environment variables. See the
[example configuration file](config.yaml.example). Available parameters can be
found through `zabbixci --help`.

## Usage

### Repository structure

ZabbixCI creates a Git repository following a specific folder structure. Zabbix
template groups are used to create folders, and templates are stored as JSON
files within these folders. For this, the most specific template group matching
the parent group variable is used to determine the path of the template. For
example, a template in the group `Templates/Operating Systems/Linux` will be
stored in the folder `Operating Systems/Linux` when `root_template_group` is set
to `Templates`.

### Managing templates

There are three methods available for ZabbixCI: `pull`, `push`, and
`clearcache`.

- The `pull` method will pull templates from the Git repository and import them
  to the Zabbix server.
- The `push` method will export templates from the Zabbix server and push them
  to the Git repository.
- The `clearcache` method clears the local github repository, needed after
  changing the git remote.

```bash
zabbixci --config config.yaml pull

zabbixci --config config.yaml push

zabbixci clearcache
```

By default, ZabbixCI outputs warnings and errors. To see debug information, use
the `-v` for a info level or `-vv` for a debug level. `-vvv` is also available
which puts all underlying API calls and Python modules in debug mode.

### Managing foreign templates

By foreign templates, we mean template exports that were not created by
ZabbixCI. (Example: the official Zabbix templates repository)

ZabbixCI can also be used to import an unstructured github repository containing
templates to a Zabbix server. The foreign repository should contain Zabbix
exports in yaml format, when this repository is used as a source for the `pull`
method, ZabbixCI will import the templates to the Zabbix server. After which,
the `push` command should be used to generate the preferred repo structure in a
new repository. The `clearcache` method should be used after changing the
remote.

```bash
# Might require the option --ignore-template-version depending on the template and Zabbix version
zabbixci --config foreign_templates.yaml pull
```

Keep in mind that that foreign templates might not match your configured
`root_template_group`, in which case these templates would not be exported from
your Zabbix instance on the next `push`. Making the previously imported
templates orphaned by ZabbixCI.
