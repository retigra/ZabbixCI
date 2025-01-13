import argparse
import asyncio
import logging
import logging.config

from zabbixci.settings import Settings
from zabbixci.zabbixci import ZabbixCI

# Read command line arguments to fill the settings

logger = logging.getLogger(__name__)


def read_args():
    parser = argparse.ArgumentParser(
        description="""ZabbixCI is a tool to manage Zabbix templates in a Git repository.
        
        ZabbixCI adds version control to Zabbix templates, allowing you to track changes, synchronize templates between different Zabbix servers, and collaborate with other team members.""",
        prog="zabbixci",
    )
    parser.add_argument(
        "action",
        help="The action to perform",
        choices=["push", "pull", "clearcache"],
    )

    # Provide configuration as file
    parser.add_argument(
        "--config",
        help="Provide configuration as yaml file",
    )

    # Zabbix
    parser.add_argument(
        "--zabbix-url",
        help="Zabbix URL",
    )
    parser.add_argument(
        "--zabbix-user",
        help="Zabbix user for user/password authentication",
    )
    parser.add_argument(
        "--zabbix-password",
        help="Zabbix password for user/password authentication",
    )
    parser.add_argument(
        "--zabbix-token",
        help="Zabbix token for token authentication (preferred)",
    )

    # Git
    parser.add_argument(
        "--remote",
        help="URL of the remote git repository, supports ssh and http(s)",
    )
    parser.add_argument(
        "--pull-branch",
        help="Branch to pull from",
    )
    parser.add_argument(
        "--push-branch",
        help="Branch to push to",
    )
    parser.add_argument(
        "--git-username",
        help="Git username, used for http(s) authentication",
    )
    parser.add_argument(
        "--git-password",
        help="Git password, used for http(s) authentication",
    )
    parser.add_argument(
        "--git-pubkey",
        help="SSH public key, used for ssh authentication",
    )
    parser.add_argument(
        "--git-privkey",
        help="SSH private key, used for ssh authentication",
    )
    parser.add_argument(
        "--git-keypassphrase",
        help="SSH key passphrase, used for ssh authentication",
    )

    # ZabbixCI
    parser.add_argument(
        "--root-template-group",
        help="Zabbix Template Group root, defaults to Templates",
    )
    parser.add_argument(
        "--template-prefix-path",
        help="The path in the git repository, used to store the templates",
    )
    parser.add_argument(
        "--template-whitelist",
        help="Comma separated list of templates to include",
    )
    parser.add_argument(
        "--template-blacklist",
        help="Comma separated list of templates to exclude",
    )
    parser.add_argument(
        "--cache",
        help="Cache path for git repository, defaults to ./cache",
    )
    parser.add_argument(
        "--dry-run",
        help="Dry run, only show changes",
        action="store_true",
        default=None,
    )

    # ZabbixCI advanced
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
        "--batch-size",
        help="Batch size for Zabbix API export requests",
    )
    parser.add_argument(
        "--ignore-template-version",
        help="Ignore template versions on import, useful for initial import",
        action="store_true",
        default=None,
    )
    parser.add_argument(
        "--insecure-ssl-verify",
        help="Disable SSL verification for Zabbix API and git, only use for testing",
        action="store_true",
        default=None,
    )
    parser.add_argument(
        "--ca-bundle",
        help="Path to CA bundle for SSL verification",
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

    settings_debug = {
        **Settings.__dict__,
        "ZABBIX_PASSWORD": "********",
        "ZABBIX_TOKEN": "********",
        "REMOTE": "********",
    }

    logger.debug(f"Settings: {settings_debug}")

    if args.action == "clearcache":
        ZabbixCI.cleanup_cache(full=True)
    else:
        asyncio.run(run_zabbixci(args.action))


async def run_zabbixci(action: str):
    zabbixci = ZabbixCI()
    await zabbixci.create_zabbix()

    try:
        if action == "push":
            await zabbixci.push()

        elif action == "pull":
            await zabbixci.pull()
    except KeyboardInterrupt:
        logger.error("Interrupted by user")

    finally:
        logger.info("Logging out")
        await zabbixci._zabbix.zapi.logout()
        await zabbixci._zabbix._client_session.close()


if __name__ == "__main__":
    parse_cli()
