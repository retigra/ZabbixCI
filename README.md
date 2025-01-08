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

ZabbixCI requires parameters to be set as command line arguments, a yaml
configuration or as environment variables. See the
[example configuration file](docs/config.yaml.example).

## Usage

Please see [Docs](docs/README.md) for extended details on usage.
The `zabbixci` command can be used to synchronize Zabbix templates with a Git
repository. 

```bash
zabbixci --help
```

# Contributing

Contributions are welcome! Please take a look at the following guidelines:

- Commit messages should follow the [Gitmoji](https://gitmoji.dev/) convention.
- Code should be formatted using
  [black](https://black.readthedocs.io/en/stable/).

# License

This project is licensed under AGPL-3.0, see [LICENSE](LICENSE.txt) for more
information.
