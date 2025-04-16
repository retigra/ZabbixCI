import logging
from os import environ

from zabbixci.settings import Settings

grey = "\x1b[38;20m"
yellow = "\x1b[33;20m"
red = "\x1b[31;20m"
bold_red = "\x1b[31;1m"
reset = "\x1b[0m"


class CustomFormatter(logging.Formatter):

    log_format = "%(asctime)s  [%(levelname)s]: %(message)s"
    formats: dict[str, str] = {}

    def __init__(self):
        super().__init__()

        if Settings.DEBUG or Settings.DEBUG_ALL:
            self.log_format = "%(asctime)s [%(name)s]  [%(levelname)s]: %(message)s"

        term = environ.get("TERM", "dumb")
        no_color = environ.get("NO_COLOR", "false")

        if term == "dumb" or no_color.lower() == "true":
            self.formats = {
                logging.DEBUG: self.log_format,
                logging.INFO: self.log_format,
                logging.WARNING: self.log_format,
                logging.ERROR: self.log_format,
                logging.CRITICAL: self.log_format,
            }
        else:
            self.formats = {
                logging.DEBUG: grey + self.log_format + reset,
                logging.INFO: grey + self.log_format + reset,
                logging.WARNING: yellow + self.log_format + reset,
                logging.ERROR: red + self.log_format + reset,
                logging.CRITICAL: bold_red + self.log_format + reset,
            }

    def format(self, record):
        log_fmt = self.formats.get(record.levelno)
        formatter = logging.Formatter(log_fmt, "%Y-%m-%d %H:%M:%S")
        return formatter.format(record)


class StatusCodeHandler(logging.Handler):
    """
    Log handler that sets a status code based on the received logs
    """

    status_code: int = 0

    def emit(self, record):
        if record.levelno >= logging.ERROR:
            self.status_code = 1
