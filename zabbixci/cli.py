import argparse
import asyncio
import logging
from sys import argv, exit, version_info
from typing import Sequence

from zabbixci._version import __version__
from zabbixci.cache.cache import Cache
from zabbixci.cache.cleanup import Cleanup
from zabbixci.exceptions import BaseZabbixCIException
from zabbixci.logging import CustomFormatter, StatusCodeHandler
from zabbixci.settings import Settings
from zabbixci.zabbixci import ZabbixCI

logger = logging.getLogger(__name__)


class CustomArgumentGroup(argparse._ArgumentGroup):
    """
    Customized ArgumentGroup with supporting code to calculate the explicit arguments
    """

    def __init__(self, container, title=None, description=None, **kwargs):
        super().__init__(container, title=None, description=None, **kwargs)
        self._container = container

    def add_argument(self, *args, **kwargs):
        if "explicit" in kwargs:
            self._container.explicit_arguments.extend(args)
            del kwargs["explicit"]

        return super().add_argument(*args, **kwargs)


class CustomArgumentParser(argparse.ArgumentParser):
    """
    Customized ArgumentParser with supporting code to calculate the explicit arguments, and parse them for boolean values when they are set explicitly (key=value)
    """

    explicit_arguments: list[str] = []

    def parse_args(self, args: Sequence[str] | None = None, namespace=None):
        """
        Default parse_args method, but with the ability to set explicit arguments to `true` when they are set without a value
        """
        argument_list: list[str] = []

        if args is None:
            argument_list = argv[1:]
        else:
            argument_list = list(args)

        for i, arg in enumerate(argument_list):
            if arg in self.explicit_arguments:
                # Explicit arguments are set to true when provided.
                argument_list.insert(i + 1, "true")
            elif [
                explicit
                for explicit in self.explicit_arguments
                if arg.startswith(f"{explicit}=")
            ]:
                # Only when the user explicitly sets a value (key=value) we parse it as a boolean
                # (no need to add true after the key, the default parser will handle it)
                break

        return super().parse_args(argument_list, namespace)

    def add_argument(self, *args, **kwargs):
        # Add the explicit argument to the list of explicit arguments
        if "explicit" in kwargs:
            self.explicit_arguments.append(kwargs["explicit"])
            del kwargs["explicit"]

        return super().add_argument(*args, **kwargs)

    # Add a custom argument group to the parser, which fills the explicit arguments list
    def add_argument_group(self, *args, **kwargs):
        group = CustomArgumentGroup(self, *args, **kwargs)
        self._action_groups.append(group)
        return group


# Custom function to handle boolean conversion
def str2bool(value):
    if isinstance(value, bool):
        return value
    if value.lower() in ("yes", "true", "t", "1"):
        return True
    elif value.lower() in ("no", "false", "f", "0"):
        return False
    else:
        raise argparse.ArgumentTypeError("Boolean value expected.")


def read_args(args: list[str] | None = None):
    method_parser = CustomArgumentParser(
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
        "--icon-map-prefix-path",
        help="The path in the git repository, used to store the icon maps",
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
        "--image-whitelist",
        help="Comma separated list of images to include",
    )
    zabbixci_group.add_argument(
        "--image-blacklist",
        help="Comma separated list of images to exclude",
    )
    zabbixci_group.add_argument(
        "--icon-map-whitelist",
        help="Comma separated list of icon maps to include",
    )
    zabbixci_group.add_argument(
        "--icon-map-blacklist",
        help="Comma separated list of icon maps to exclude",
    )
    zabbixci_group.add_argument(
        "--cache-path",
        help="Cache path for git repository, defaults to ./cache",
    )
    zabbixci_group.add_argument(
        "--dry-run",
        help="Enable or disable dry run.",
        const=True,
        default=None,
        type=str2bool,
        nargs="?",
        explicit=True,
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
        explicit=True,
    )
    zabbixci_group.add_argument(
        "--sync-templates",
        help="Synchronize templates between Zabbix and git",
        const=True,
        default=None,
        type=str2bool,
        nargs="?",
        explicit=True,
    )
    zabbixci_group.add_argument(
        "--sync-icons",
        help="Synchronize icons between Zabbix and git",
        const=True,
        default=None,
        type=str2bool,
        nargs="?",
        explicit=True,
    )
    zabbixci_group.add_argument(
        "--sync-backgrounds",
        help="Synchronize background images between Zabbix and git",
        const=True,
        default=None,
        type=str2bool,
        nargs="?",
        explicit=True,
    )
    zabbixci_group.add_argument(
        "--sync-icon-maps",
        help="Synchronize icon maps between Zabbix and git",
        const=True,
        default=None,
        type=str2bool,
        nargs="?",
        explicit=True,
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
    git_group.add_argument(
        "--git-author-name",
        help="Git author name",
    )
    git_group.add_argument(
        "--git-author-email",
        help="Git author email",
    )
    git_group.add_argument(
        "-m",
        "--git-commit-message",
        help="Git commit message",
    )

    zabbixci_advanced_group = method_parser.add_argument_group("ZabbixCI advanced")

    # ZabbixCI advanced
    zabbixci_advanced_group.add_argument(
        "-v",
        "--verbose",
        help="Enable verbose logging",
        dest="verbose",
        const=True,
        default=None,
        type=str2bool,
        nargs="?",
        explicit=True,
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
        explicit=True,
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
        explicit=True,
    )
    zabbixci_advanced_group.add_argument(
        "--batch-size",
        help="Batch size for Zabbix API export requests",
    )
    zabbixci_advanced_group.add_argument(
        "--ignore-template-version",
        help="Ignore template versions on import, useful for initial import",
        const=True,
        default=None,
        type=str2bool,
        nargs="?",
        explicit=True,
    )
    zabbixci_advanced_group.add_argument(
        "--insecure-ssl-verify",
        help="Disable SSL verification for Zabbix API and git, only use for testing",
        const=True,
        default=None,
        type=str2bool,
        nargs="?",
        explicit=True,
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
        explicit=True,
    )

    return method_parser.parse_args(args)


def parse_cli(custom_args: list[str] | None = None):
    """
    Run ZabbixCI reading the command line arguments

    param custom_args: Custom arguments to parse instead of reading from the command line
    """
    Settings.from_env()

    args = read_args(custom_args)
    arguments = vars(args)

    if args.config:
        Settings.read_config(args.config)

    for key, value in arguments.items():
        if value is not None:
            setattr(Settings, key.upper(), value)

    global_level = (
        logging.DEBUG
        if Settings.DEBUG_ALL
        else logging.INFO if Settings.VERBOSE else logging.WARN
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
        if Settings.DEBUG or Settings.DEBUG_ALL
        else logging.INFO if Settings.VERBOSE else logging.WARN
    )

    settings_debug = {
        **Settings.__dict__,
        "ZABBIX_PASSWORD": "********",
        "ZABBIX_TOKEN": "********",
        "REMOTE": "********",
    }

    logger.debug("Settings: %s", settings_debug)

    Cache(Settings.CACHE_PATH)

    if args.action == "clearcache":
        Cleanup.cleanup_cache(full=True)
    else:
        asyncio.run(run_zabbixci(args.action))


async def run_zabbixci(action: str):
    zabbixci = ZabbixCI()

    status_handler = StatusCodeHandler()
    logging.getLogger().addHandler(status_handler)

    exit_code = 0

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
        exit_code = 130
    except SystemExit as e:
        logger.debug("Script exited with code %s", e.code)
        exit_code = int(e.code or 1)
    except BaseZabbixCIException as e:
        logger.error(e)
        exit_code = 1
    except Exception:
        logger.error("Unexpected error:", exc_info=True)
        exit_code = 129
    finally:
        if zabbixci._zabbix:
            await zabbixci._zabbix.zapi.logout()
            await zabbixci._zabbix.zapi.client_session.close()

        # No exception was raised, return status code from logger
        if exit_code == 0:
            exit_code = status_handler.status_code

        if exit_code != 0:
            logger.error("ZabbixCI run completed with errors")
        exit(exit_code)


if __name__ == "__main__":
    parse_cli()
