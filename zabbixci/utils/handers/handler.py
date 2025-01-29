import logging
from abc import ABCMeta, abstractmethod

import regex

from zabbixci.settings import Settings

logger = logging.getLogger(__name__)


class Handler(object, metaclass=ABCMeta):
    @abstractmethod
    def _get_whitelist(self) -> list[str] | str:
        raise NotImplementedError()

    @abstractmethod
    def _get_blacklist(self) -> list[str] | str:
        raise NotImplementedError()

    def _use_regex(self) -> bool:
        return Settings.REGEX_MATCHING

    def _enforce_whitelist(self, query: str):
        """
        Match a query against the whitelist, if no whitelist is set all queries are allowed.

        :param query: Query to match
        :return: True when the template was blocked, False when the template was allowed
        """
        if not self._get_whitelist():
            return False

        if self._use_regex():
            pattern = regex.compile(self._get_whitelist())
            return pattern.fullmatch(query) is None
        else:
            return query not in self._get_whitelist()

    def _enforce_blacklist(self, query: str):
        """
        Match a query against the blacklist, if no blacklist is set all queries are allowed.

        :param query: Query to match
        :return: True when the template was blocked, False when the template was allowed
        """
        if not self._get_blacklist():
            return False

        if self._use_regex():
            pattern = regex.compile(self._get_blacklist())
            return pattern.fullmatch(query) is not None
        else:
            return query in self._get_blacklist()
