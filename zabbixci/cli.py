import argparse
import logging.config
from zabbixci.settings import Settings

import logging

# Read command line arguments to fill the settings

logger = logging.getLogger(__name__)


def read_args():
    parser = argparse.ArgumentParser(description="Zabbix to Git")
    parser.add_argument(
        "action",
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
        "-v",
        help="Enable verbose logging",
        action="store_true",
        dest="verbose",
    )
    parser.add_argument(
        "-vv",
        "--debug",
        help="Enable debug logging",
        action="store_true",
        dest="debug",
    )
    parser.add_argument(
        "-vvv",
        "--debug-all",
        help="Enable debug logging for all modules",
        action="store_true",
        dest="debug_all",
    )

    parser.add_argument(
        "--config",
        help="The configuration file",
    )

    return parser.parse_args()


def parse_cli():
    Settings.from_env()
    args = read_args()
    arguments = vars(args)

    global_level = (
        logging.DEBUG
        if args.debug_all
        else logging.INFO if args.verbose else logging.WARN
    )

    logging.basicConfig(
        format="%(asctime)s [%(name)s]  [%(levelname)s]: %(message)s",
        level=global_level,
    )

    zabbixci_logger = logging.getLogger("zabbixci")
    zabbixci_logger.setLevel(
        logging.DEBUG
        if args.debug or args.debug_all
        else logging.INFO if args.verbose else logging.WARN
    )

    if args.config:
        Settings.read_config(args.config)

    for key, value in arguments.items():
        if value is not None:
            logger.debug(f"Setting {key} to {value}")
            setattr(Settings, key.upper(), value)

    from zabbixci import main

    settings_debug = {
        **Settings.__dict__,
        "ZABBIX_PASSWORD": "********",
        "ZABBIX_TOKEN": "********",
        "REMOTE": "********",
    }

    logger.debug(f"Settings: {settings_debug}")

    if args.action == "push":
        main.push()

    elif args.action == "pull":
        main.pull()


if __name__ == "__main__":
    parse_cli()
