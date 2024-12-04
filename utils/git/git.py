import pygit2
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

    def switch_branch(self, branch: str):
        """
        Switch to a branch, if the branch does not exist, create it
        """
        if branch not in self.repository.branches.local:
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
