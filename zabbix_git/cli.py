import argparse
import settings

import logging
import dotenv

# Read command line arguments to fill the settings


def read_args():
    parser = argparse.ArgumentParser(description="Zabbix to Git")
    parser.add_argument(
        'action',
        help="The action to perform",
        choices=["push", "pull"],
    )
    parser.add_argument(
        "--remote",
        help="The remote repository to push to",
        default=settings.REMOTE,
    )
    parser.add_argument(
        "--cache",
        help="The cache path to store the Zabbix templates",
        default=settings.CACHE_PATH,
    )
    parser.add_argument(
        "--debug",
        help="Enable debug logging",
        action="store_true",
    )
    parser.add_argument(
        "--dotenv",
        help="Path to the .env file",
        default=".env",
    )
    return parser.parse_args()


def parse_cli():
    args = read_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

        zabbix_logger = logging.getLogger("zabbix_utils")
        zabbix_logger.setLevel(logging.INFO)
    else:
        logging.basicConfig(level=logging.INFO)

    settings.REMOTE = args.remote
    settings.CACHE_PATH = args.cache

    if args.dotenv:
        logging.info(f"Loading environment variables from {args.dotenv}")
        dotenv.load_dotenv(args.dotenv)

        settings.get_settings()

    import main

    if args.action == "push":
        main.push()

    elif args.action == "pull":
        main.pull()


if __name__ == "__main__":
    parse_cli()
