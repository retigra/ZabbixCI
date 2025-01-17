![ZabbixCI cog logo](https://raw.githubusercontent.com/retigra/zabbixci/main/logo.png "ZabbixCI logo")

![PyPI - Version](https://img.shields.io/pypi/v/zabbixci)
![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/retigra/ZabbixCI/pypi.yml?label=pypi%20build)
![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/retigra/ZabbixCI/ghcr.yaml?label=docker%20build)


> [!WARNING]
> This project is under active development, the code in the main branch should be relatively stable but things might break every now and then.
> The releases that can be installed with `pip` are currently stable enough for testing.
> If you run into unexpected bugs, please create an [issue](https://github.com/retigra/ZabbixCI/issues/new).
> For questions about usage, please start a [discussion](https://github.com/retigra/ZabbixCI/discussions/new?category=q-a).

# ZabbixCI

ZabbixCI is a tool that adds continuous integration to Zabbix, allowing you to
synchronize Zabbix assets with a Git repository. By using the Zabbix API,
ZabbixCI can create, update, and delete templates across multiple Zabbix
servers.

> [!NOTE]
> ZabbixCI has no affiliation with [Zabbix SIA](https://www.zabbix.com).

## Features

ZabbixCI provides the following features:

* Easily installable through pip or docker, depending on your need
* Export templates from Zabbix and push them to Git
* Pull templates from Git and import them in Zabbix
* Only changed or new templates will be processed during Git push or Zabbix import actions
* Removes deleted templates automatically (unless black- or whitelisting is used)
* Fully configurable through cli arguments, config file or environment variables
* Supports HTTP(S) and SSH auth for Git
* Build with parallelization in mind to speed up the process (can be scaled for your needs)
* Built-in version compatibility checking
* Use dry runs to verify behavior without changes to Zabbix or Git
* (Optional) Support for private CA servers to verify certificates
* (Optional) Allow black-/whitelisting of templates
* (Optional) Use separate branches for push and pull transactions
* (Optional) Allow automatic versioning of exported templates based on timestamps
* (Optional) Automatically populate vendor field in templates


## Installation

ZabbixCI is available on [PyPI](https://pypi.org/project/zabbixci/) and can be
installed using pip:

```bash
pip install zabbixci
```

Alternatively, you can use a container image to run ZabbixCI, see the available
[container images](https://github.com/retigra/ZabbixCI/pkgs/container/zabbixci).
See the
[Containerized Deployment](https://github.com/retigra/ZabbixCI/blob/main/docs/Containerized.md)
documentation for more information.

## Configuration

ZabbixCI requires parameters to be set as command line arguments, a yaml
configuration or as environment variables. See the
[example configuration file](https://github.com/retigra/ZabbixCI/tree/main/docs/config.yaml.example).

We recommend passing environment variables when using the container image. Feel
free to use the method that best suits your workflow.

## Usage

Please see [Docs](https://github.com/retigra/ZabbixCI/tree/main/docs/README.md)
for extended details on usage. The `zabbixci` command can be used to synchronize
Zabbix templates with a Git repository. `--help` will give you an overview of
the options.

```bash
zabbixci --help
```

# License

This project is licensed under AGPL-3.0, see
[LICENSE](https://github.com/retigra/ZabbixCI/tree/main/LICENSE.txt) for more
information.

# Contributing

Contributions are welcome! Please take a look at the following guidelines:

- Commit messages should follow the [Gitmoji](https://gitmoji.dev/) convention.
- Code should be formatted using
  [black](https://black.readthedocs.io/en/stable/).

## Star History

> [!NOTE]
> If you like this project, please consider starring it on GitHub. ❤️

<a href="https://star-history.com/#retigra/ZabbixCI&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=retigra/ZabbixCI&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=retigra/ZabbixCI&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=retigra/ZabbixCI&type=Date" />
 </picture>
</a>
