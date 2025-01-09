![ZabbixCI cog logo](https://raw.githubusercontent.com/retigra/zabbixci/main/logo.png "ZabbixCI logo")

![PyPI - Version](https://img.shields.io/pypi/v/zabbixci)
![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/retigra/ZabbixCI/pypi.yml?label=pypi%20build)
![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/retigra/ZabbixCI/ghcr.yaml?label=docker%20build)

# ZabbixCI

ZabbixCI is a tool that adds continuous integration to Zabbix, allowing you to
synchronize Zabbix assets with a Git repository. By using the Zabbix API,
ZabbixCI can create, update, and delete templates across multiple Zabbix
servers.

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
documentation for more

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

# Contributing

Contributions are welcome! Please take a look at the following guidelines:

- Commit messages should follow the [Gitmoji](https://gitmoji.dev/) convention.
- Code should be formatted using
  [black](https://black.readthedocs.io/en/stable/).

# License

This project is licensed under AGPL-3.0, see
[LICENSE](https://github.com/retigra/ZabbixCI/tree/main/LICENSE.txt) for more
information.
