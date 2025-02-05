import logging
import ssl
import urllib.error
from urllib.request import Request, urlopen

import pygit2

from zabbixci.exceptions import GitException
from zabbixci.settings import Settings

logger = logging.getLogger(__name__)


class RemoteCallbacksSecured(pygit2.RemoteCallbacks):
    _credentials = None

    _call_count = 0
    _agent_active: bool = False

    def __init__(self, credentials):
        super().__init__()
        self._credentials = credentials

    def credentials(self, url, username_from_url, allowed_types):
        self._call_count += 1
        if self._call_count > 10 and not self._agent_active:
            raise GitException(
                "SSH agent was unable to provide credentials, is your key added to the agent?"
            )

        return self._credentials(url, username_from_url, allowed_types)

    def mark_agent_active(self):
        self._agent_active = True

    def transfer_progress(self, stats):
        logger.debug(
            f"Git: Transferred {stats.received_objects} objects, "
            f"{stats.indexed_objects} indexed, "
            f"{stats.total_objects} total"
        )
        return True

    def certificate_check(self, cert, valid, hostname):
        return valid


class GitCredentials:
    _ssl_context = None
    _ssl_valid: bool = False

    def __init__(self):
        if Settings.CA_BUNDLE:
            self._ssl_context = ssl.create_default_context()
            self._ssl_context.load_verify_locations(Settings.CA_BUNDLE)

    def _validate_ssl_cert(self, _cert: None, valid: bool, hostname: bytes):
        """
        Callback function for pygit2 RemoteCallbacks object to validate SSL certificates
        """
        hostname_str = hostname.decode("utf-8")

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
            resp = urlopen(req, context=self._ssl_context)

            logger.debug(f"Response from {hostname_str}: {resp.status}")

            self._ssl_valid = True
            return True
        except urllib.error.URLError as e:
            logger.error(f"Error validating SSL certificate: {e}")
            return False

    def create_git_callback(self):
        """
        Create a pygit2 RemoteCallbacks object with the appropriate credentials
        Handles both username/password and SSH keypair authentication
        """
        if Settings.GIT_USERNAME and Settings.GIT_PASSWORD:
            logger.debug("Using username and password for Git authentication")
            credentials = pygit2.UserPass(Settings.GIT_USERNAME, Settings.GIT_PASSWORD)
        elif Settings.GIT_PUBKEY and Settings.GIT_PRIVKEY:
            logger.debug("Using SSH keypair for Git authentication")
            credentials = pygit2.Keypair(
                Settings.GIT_USERNAME,
                Settings.GIT_PUBKEY,
                Settings.GIT_PRIVKEY,
                Settings.GIT_KEYPASSPHRASE,
            )
        else:
            logger.debug("Using SSH agent for Git authentication")
            credentials = pygit2.KeypairFromAgent(Settings.GIT_USERNAME)

        git_cb = RemoteCallbacksSecured(
            credentials,
        )

        if Settings.INSECURE_SSL_VERIFY:
            # Accept all certificates
            git_cb.certificate_check = lambda cert, valid, hostname: True
        elif Settings.CA_BUNDLE:
            # Validate certificates with the provided CA bundle
            git_cb.certificate_check = self._validate_ssl_cert

        return git_cb
