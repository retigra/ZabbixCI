import pygit2
from pygit2.enums import MergeAnalysis
import logging
import os

logger = logging.getLogger(__name__)


class Git:
    repository: pygit2.Repository = None
    author = pygit2.Signature("Zabbix Configuration", "zabbix@example.com")

    def __init__(self, path: str = None):
        """
        Initialize git repository
        :param path: Path to the git repository, defaults to ./cache
        """
        if not path:
            path = "./cache"

        if not os.path.exists(path):
            os.makedirs(path)

        if not os.path.exists(f"{path}/.git"):
            self.repository = pygit2.init_repository(path, initial_head="main")
        else:
            self.repository = pygit2.Repository(path)

    @property
    def has_changes(self):
        """
        Check if the repository has changes, returns True if there are changes, False otherwise
        """
        return len(self.repository.status()) > 0

    @property
    def current_branch(self):
        """
        Get the current branch
        """
        return self.repository.head.shorthand

    def get_current_revision(self):
        """
        Get the current revision
        """
        return self.repository.head.target

    def diff(self, old_revision: str):
        """
        Get the diff of the changes
        """
        return self.repository.diff(old_revision)

    def switch_branch(self, branch: str):
        """
        Switch to a branch, if the branch does not exist, create it
        """
        if not self.repository.branches.local.get(branch):
            self.create_branch(branch)

        local_branch = self.repository.branches.local[branch]

        self.repository.checkout(local_branch)

    def create_branch(self, branch: str):
        """
        Create a branch
        """
        try:
            self.repository.branches.local.create(
                branch, self.repository.head.peel())
        except Exception as e:
            logger.error(f"Failed to create branch: {e}")

    def add_all(self):
        """
        Add all changes to the index
        """
        index = self.repository.index
        index.add_all()
        index.write()

    def commit(self, message: str):
        """
        Commit current index to the repository
        """
        index = self.repository.index
        index.write()

        tree = index.write_tree()

        self.repository.create_commit(
            "HEAD",
            self.author,
            self.author,
            message,
            tree,
            [self.repository.head.target] if not self.repository.head_is_unborn else []
        )

    def push(self, remote_url: str, credentials, branch: str = None):
        """
        Push the changes to the remote repository
        """
        remote = self.repository.remotes['origin']

        if not branch:
            branch = self.repository.head.shorthand

        if not remote:
            remote = self.repository.remotes.create('origin', remote_url)

        callbacks = pygit2.RemoteCallbacks(credentials=credentials)

        remote.push([f"refs/heads/{branch}"], callbacks=callbacks)

    def pull(self, remote_url: str, credentials, branch: str = None):
        """
        Pull the changes from the remote repository, merge them with the local repository
        """
        remote = self.repository.remotes['origin']

        if not branch:
            branch = self.repository.head.shorthand

        if not remote:
            remote = self.repository.remotes.create('origin', remote_url)

        callbacks = pygit2.RemoteCallbacks(credentials=credentials)

        remote.fetch(callbacks=callbacks)

        remote_id = self.repository.lookup_reference(
            f"refs/remotes/origin/{branch}").target

        merge_result, _ = self.repository.merge_analysis(remote_id)

        if merge_result & MergeAnalysis.UP_TO_DATE:
            logger.info("Already up to date")
            return

        if merge_result & MergeAnalysis.FASTFORWARD:
            self.repository.checkout_tree(self.repository.get(remote_id))
            self.repository.head.set_target(remote_id)
            self.repository.head.set_target(remote_id)
            return

        if merge_result & MergeAnalysis.NORMAL:
            self.repository.merge(remote_id)

            if self.repository.index.conflicts:
                logger.error("Conflicts detected")
                return

        self.repository.state_cleanup()
        self.commit("Merge changes")
