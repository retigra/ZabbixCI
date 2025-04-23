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
[example configuration file](config.yaml). Available parameters can be
found through `zabbixci --help`.

## Usage

### Repository structure

ZabbixCI creates a Git repository following a specific folder structure. 
For templates, Zabbix template groups are used to create folders, and templates are stored 
as yaml files within these folders. 

For this, the most parent template group matching the `root_template_group` is used 
to determine the path of the template. 
For example, a template in the group `Templates/Operating Systems/Linux` will be
stored in the folder `Operating Systems/Linux` when `root_template_group` is set
to `Templates`.

Images within Git are located in the folder set by `image_prefix_path`, which is `images` by default.
This folder can contain the following folder structure:

```bash
images/
├── backgrounds
├── icons
├── source-backgrounds
└── source-icons
```

`backgrounds` and `icons` will contain the synced images of those types.
The `source-backgrounds` and `source-icons` can be filled with image sources that 
can be used to autogenerate Zabbix images in the desired sizes. 

Use the methods `generate-backgrounds` or `generate-icons` with the option 
`--background-sizes` or `--icon-sizes` respectively to populate the 
`backgrounds` and `icons` folders with the desired files to sync. 

### Managing assets

The main methods available for ZabbixCI are: `pull`, `push`, and
`clearcache`.

- The `pull` method will pull assets from the Git repository and import them
  into the Zabbix server.
- The `push` method will export assets from the Zabbix server and push them
  to the Git repository.
- The `clearcache` method clears the local github repository, this is needed after
  changing the git remote.

```bash
zabbixci --config config.yaml pull

zabbixci --config config.yaml push

zabbixci clearcache
```

By default, ZabbixCI outputs warnings and errors. To see more information, use
the `-v` for a info level or `-vv` for a debug level. `-vvv` is also available
which puts all underlying API calls and Python modules in debug mode.

### Managing foreign templates

By foreign templates, we mean template exports that were not created by
ZabbixCI. (Example: the official Zabbix templates repository)

ZabbixCI can also be used to import an unstructured github repository containing
templates to a Zabbix server. The foreign repository should contain Zabbix
exports in _yaml_ format, when this repository is used as a source for the `pull`
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

## Tutorials

For practical guides on using ZabbixCI, check out our [tutorials](https://github.com/retigra/ZabbixCI/tree/main/docs/tutorials) section.
