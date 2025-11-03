import logging
import ssl
import urllib.error
from urllib.request import Request, urlopen

import pygit2

from zabbixci.exceptions import GitError
from zabbixci.settings import ApplicationSettings

logger = logging.getLogger(__name__)


SSH_AGENT_CALL_TIMEOUT = 10


class RemoteCallbacksSecured(pygit2.RemoteCallbacks):
    _credentials: pygit2.UserPass | pygit2.Keypair | pygit2.KeypairFromAgent

    _call_count = 0
    _agent_active: bool = False

    def __init__(self, credentials):
        super().__init__()
        self._credentials = credentials

    def credentials(self, url, username_from_url, allowed_types):
        self._call_count += 1
        if self._call_count > SSH_AGENT_CALL_TIMEOUT and not self._agent_active:
            raise GitError(
                "SSH agent was unable to provide credentials, is your key added to the agent?"
            )

        return self._credentials(url, username_from_url, allowed_types)

    def mark_agent_active(self):
        self._agent_active = True

    def transfer_progress(self, stats):
        logger.debug(
            "Git: Transferred %s objects, %s indexed, %s total",
            stats.received_objects,
            stats.indexed_objects,
            stats.total_objects,
        )
        return True

    def certificate_check(self, certificate, valid, host):
        return valid


class GitCredentials:
    _ssl_context: ssl.SSLContext
    _ssl_valid: bool = False
    settings: ApplicationSettings

    def __init__(self, settings: ApplicationSettings):
        self.settings = settings

        if self.settings.CA_BUNDLE:
            self._ssl_context = ssl.create_default_context()
            self._ssl_context.load_verify_locations(self.settings.CA_BUNDLE)

    def _validate_ssl_cert(self, certificate: None, valid: bool, host: bytes):
        """
        Callback function for pygit2 RemoteCallbacks object to validate SSL certificates
        """
        hostname_str = host.decode("utf-8")

        if valid:
            # If native SSL validation is successful, we can skip the custom check
            return True

        if self._ssl_valid:
            # If the certificate has already been validated, we can skip the check
            return True

        # Check if the certificate matches in SSL context
        # Certificate is not given by pygit2, so we request it ourselves
        # by making a request to the hostname with urllib
        try:
            req = Request(
                f"https://{hostname_str}",
                method="GET",
            )
            resp = urlopen(req, context=self._ssl_context)  # noqa: S310

            logger.debug("Response from %s: %s", hostname_str, resp.status)

            self._ssl_valid = True
            return True
        except urllib.error.URLError as e:
            logger.error("Error validating SSL certificate: %s", e)
            return False

    def create_git_callback(self):
        """
        Create a pygit2 RemoteCallbacks object with the appropriate credentials
        Handles both username/password and SSH keypair authentication
        """
        if self.settings.GIT_USERNAME and self.settings.GIT_PASSWORD:
            logger.debug("Using username and password for Git authentication")
            credentials = pygit2.UserPass(
                self.settings.GIT_USERNAME, self.settings.GIT_PASSWORD
            )
        elif self.settings.GIT_PUBKEY and self.settings.GIT_PRIVKEY:
            logger.debug("Using SSH keypair for Git authentication")
            credentials = pygit2.Keypair(
                self.settings.GIT_USERNAME,
                self.settings.GIT_PUBKEY,
                self.settings.GIT_PRIVKEY,
                self.settings.GIT_KEYPASSPHRASE,
            )
        else:
            logger.debug("Using SSH agent for Git authentication")
            credentials = pygit2.KeypairFromAgent(self.settings.GIT_USERNAME)

        git_cb = RemoteCallbacksSecured(
            credentials,
        )

        if self.settings.INSECURE_SSL_VERIFY:
            # Accept all certificates
            git_cb.certificate_check = lambda certificate, valid, host: True
        elif self.settings.CA_BUNDLE:
            # Validate certificates with the provided CA bundle
            git_cb.certificate_check = self._validate_ssl_cert

        return git_cb
