import argparse
import asyncio
import logging
import logging.config
from sys import version_info

from zabbixci._version import __version__
from zabbixci.exceptions import BaseZabbixCIException
from zabbixci.logging import CustomFormatter
from zabbixci.settings import Settings
from zabbixci.utils.cache.cache import Cache
from zabbixci.utils.cache.cleanup import Cleanup
from zabbixci.zabbixci import ZabbixCI

# Read command line arguments to fill the settings

logger = logging.getLogger(__name__)


def str2bool(value: str):
    """Convert various string representations of boolean values."""
    if isinstance(value, bool):
        return value
    if value.lower() in ("true", "1", "yes", "y"):
        return True
    elif value.lower() in ("false", "0", "no", "n", "f"):
        return False
    raise argparse.ArgumentTypeError(f"Invalid boolean value: {value}")


def read_args():
    method_parser = argparse.ArgumentParser(
        description="ZabbixCI is a tool to manage Zabbix templates in a Git repository. ZabbixCI adds version control to Zabbix templates, allowing you to track changes, synchronize templates between different Zabbix servers, and collaborate with other team members.",
        prog="zabbixci",
    )
    method_parser.add_argument(
        "action",
        help="The action to perform",
        choices=[
            "push",
            "pull",
            "clearcache",
            "version",
            "generate-icons",
            "generate-backgrounds",
        ],
    )

    # Provide configuration as file
    method_parser.add_argument(
        "-c",
        "--config",
        help="Provide configuration as YAML file",
    )

    zabbixci_group = method_parser.add_argument_group("ZabbixCI")

    # ZabbixCI
    zabbixci_group.add_argument(
        "--root-template-group",
        help="Zabbix Template Group root, defaults to Templates",
    )
    zabbixci_group.add_argument(
        "--template-prefix-path",
        help="The path in the git repository, used to store the templates",
    )
    zabbixci_group.add_argument(
        "--image-prefix-path",
        help="The path in the git repository, used to store the images",
    )
    zabbixci_group.add_argument(
        "--template-whitelist",
        help="Comma separated list of templates to include",
    )
    zabbixci_group.add_argument(
        "--template-blacklist",
        help="Comma separated list of templates to exclude",
    )
    zabbixci_group.add_argument(
        "--cache",
        help="Cache path for git repository, defaults to ./cache",
    )
    zabbixci_group.add_argument(
        "--dry-run",
        help="Dry run, only show changes",
        const=True,
        default=None,
        type=str2bool,
        nargs="?",
    )
    zabbixci_group.add_argument(
        "--vendor",
        help="Vendor name for templates",
        default=None,
    )
    zabbixci_group.add_argument(
        "--set-version",
        help="Set version on import",
        const=True,
        default=None,
        type=str2bool,
        nargs="?",
    )
    zabbixci_group.add_argument(
        "--sync-templates",
        help="Synchronize templates between Zabbix and git",
        const=True,
        default=None,
        type=str2bool,
        nargs="?",
    )
    zabbixci_group.add_argument(
        "--sync-icons",
        help="Synchronize icons between Zabbix and git",
        const=True,
        default=None,
        type=str2bool,
        nargs="?",
    )
    zabbixci_group.add_argument(
        "--sync-backgrounds",
        help="Synchronize background images between Zabbix and git",
        const=True,
        default=None,
        type=str2bool,
        nargs="?",
    )
    zabbixci_group.add_argument(
        "--image-whitelist",
        help="Comma separated list of images to include",
    )
    zabbixci_group.add_argument(
        "--image-blacklist",
        help="Comma separated list of images to exclude",
    )
    zabbixci_group.add_argument(
        "--icon-sizes",
        help="Comma separated list of icon sizes to generate",
    )
    zabbixci_group.add_argument(
        "--background-sizes",
        help="Comma separated list of background sizes to generate",
    )

    zabbix_group = method_parser.add_argument_group("Zabbix")

    # Zabbix
    zabbix_group.add_argument(
        "--zabbix-url",
        help="Zabbix URL",
    )
    zabbix_group.add_argument(
        "--zabbix-user",
        help="Zabbix user for user/password authentication",
    )
    zabbix_group.add_argument(
        "--zabbix-password",
        help="Zabbix password for user/password authentication",
    )
    zabbix_group.add_argument(
        "--zabbix-token",
        help="Zabbix token for token authentication (preferred)",
    )

    git_group = method_parser.add_argument_group("Git")

    # Git
    git_group.add_argument(
        "--remote",
        help="URL of the remote git repository, supports ssh and http(s)",
    )
    git_group.add_argument(
        "--pull-branch",
        help="Branch to pull from",
    )
    git_group.add_argument(
        "--push-branch",
        help="Branch to push to",
    )
    git_group.add_argument(
        "--git-username",
        help="Git username, used for http(s) authentication",
    )
    git_group.add_argument(
        "--git-password",
        help="Git password, used for http(s) authentication",
    )
    git_group.add_argument(
        "--git-pubkey",
        help="SSH public key, used for ssh authentication",
    )
    git_group.add_argument(
        "--git-privkey",
        help="SSH private key, used for ssh authentication",
    )
    git_group.add_argument(
        "--git-keypassphrase",
        help="SSH key passphrase, used for ssh authentication",
    )

    zabbixci_advanced_group = method_parser.add_argument_group("ZabbixCI advanced")

    # ZabbixCI advanced
    zabbixci_advanced_group.add_argument(
        "-v",
        help="Enable verbose logging",
        dest="verbose",
        const=True,
        default=None,
        type=str2bool,
        nargs="?",
    )
    zabbixci_advanced_group.add_argument(
        "-vv",
        "--debug",
        help="Enable debug logging",
        dest="debug",
        const=True,
        default=None,
        type=str2bool,
        nargs="?",
    )
    zabbixci_advanced_group.add_argument(
        "-vvv",
        "--debug-all",
        help="Enable debug logging for all modules",
        dest="debug_all",
        const=True,
        default=None,
        type=str2bool,
        nargs="?",
    )
    zabbixci_advanced_group.add_argument(
        "--batch-size",
        help="Batch size for Zabbix API export requests",
    )
    zabbixci_advanced_group.add_argument(
        "--ignore-template-version",
        help="Ignore template versions on import, useful for initial import",
        action="store_true",
        default=None,
    )
    zabbixci_advanced_group.add_argument(
        "--insecure-ssl-verify",
        help="Disable SSL verification for Zabbix API and git, only use for testing",
        const=True,
        default=None,
        type=str2bool,
        nargs="?",
    )
    zabbixci_advanced_group.add_argument(
        "--ca-bundle",
        help="Path to CA bundle for SSL verification",
    )
    zabbixci_advanced_group.add_argument(
        "--regex-matching",
        help="Use regex matching for template and image whitelists and blacklists",
        const=True,
        default=None,
        type=str2bool,
        nargs="?",
    )

    return method_parser.parse_args()


def parse_cli():
    Settings.from_env()
    args = read_args()
    arguments = vars(args)

    global_level = (
        logging.DEBUG
        if args.debug_all
        else logging.INFO if args.verbose else logging.WARN
    )

    ch = logging.StreamHandler()

    ch.setFormatter(CustomFormatter())

    logging.basicConfig(
        level=global_level,
        handlers=[ch],
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

    Cache(Settings.CACHE_PATH)

    if args.action == "clearcache":
        Cleanup.cleanup_cache(full=True)
    else:
        asyncio.run(run_zabbixci(args.action))


async def run_zabbixci(action: str):
    zabbixci = ZabbixCI()

    try:
        if action == "version":
            zapi_version = "Unknown"
            try:
                await zabbixci.create_zabbix()
            except Exception:
                pass

            if zabbixci._zabbix:
                zapi_version = str(zabbixci._zabbix.zapi.version)

            print(f"ZabbixCI version {__version__}")
            print(f"ZabbixAPI version {zapi_version}")
            print(
                f"Python version {version_info.major}.{version_info.minor}.{version_info.micro}"
            )

        elif action == "push":
            zabbixci.create_git()
            await zabbixci.create_zabbix()
            await zabbixci.push()

        elif action == "pull":
            zabbixci.create_git()
            await zabbixci.create_zabbix()
            await zabbixci.pull()

        elif action == "generate-icons":
            zabbixci.create_git()
            zabbixci.generate_images("icon")

        elif action == "generate-backgrounds":
            zabbixci.create_git()
            zabbixci.generate_images("background")

    except KeyboardInterrupt:
        logger.error("Interrupted by user")
    except SystemExit as e:
        logger.debug(f"Script exited with code {e.code}")
    except BaseZabbixCIException as e:
        logger.error(e)
    except Exception:
        logger.error("Unexpected error:", exc_info=True)
    finally:
        if zabbixci._zabbix:
            await zabbixci._zabbix.zapi.logout()
            await zabbixci._zabbix.zapi.client_session.close()


if __name__ == "__main__":
    parse_cli()
