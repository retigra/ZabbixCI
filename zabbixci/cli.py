import argparse
import logging.config
from zabbixci.settings import Settings

import logging

# Read command line arguments to fill the settings


def read_args():
    parser = argparse.ArgumentParser(description="Zabbix to Git")
    parser.add_argument(
        'action',
        help="The action to perform",
        choices=["push", "pull"],
    )
    parser.add_argument(
        "--zabbix-url",
        help="The Zabbix URL",
    )
    parser.add_argument(
        "--zabbix-user",
        help="The Zabbix user",
    )
    parser.add_argument(
        "--zabbix-password",
        help="The Zabbix password",
    )
    parser.add_argument(
        "--remote",
        help="The remote repository",
    )
    parser.add_argument(
        "--parent-group",
        help="The parent group",
    )
    parser.add_argument(
        "--pull-branch",
        help="The branch to pull",
    )
    parser.add_argument(
        "--push-branch",
        help="The branch to push",
    )
    parser.add_argument(
        "--git-prefix-path",
        help="The prefix path for the git repository",
    )
    parser.add_argument(
        "--whitelist",
        help="The whitelist of templates",
    )
    parser.add_argument(
        "--blacklist",
        help="The blacklist of templates",
    )
    parser.add_argument(
        "--cache",
        help="The cache path",
    )

    parser.add_argument(
        "--debug",
        help="Enable debug logging",
    )
    parser.add_argument(
        "--config",
        help="The configuration file",
    )

    return parser.parse_args()


def parse_cli():
    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
            },
        },
        "loggers": {
            "zabbixci": {
                "handlers": ["console"],
                "level": "INFO" if not read_args().debug else "DEBUG",
            },
        },
    })

    Settings.from_env()

    args = read_args()

    arguments = vars(args)

    for key, value in arguments.items():
        if value is not None:
            setattr(Settings, key.upper(), value)

    if args.config:
        Settings.read_config(args.config)

    from zabbixci import main

    logging.debug(f"Settings: {Settings.__dict__}")

    if args.action == "push":
        main.push()

    elif args.action == "pull":
        main.pull()


if __name__ == "__main__":
    parse_cli()
