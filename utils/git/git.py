import pygit2
import logging
import os

logger = logging.getLogger(__name__)


class Git:
    repository: pygit2.Repository = None
    author = pygit2.Signature("Zabbix Configuration", "zabbix@example.com")

    def __init__(self, path: str = None):
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
        return len(self.repository.status()) > 0

    def add_all(self):
        index = self.repository.index
        index.add_all()
        index.write()

    def commit(self, message: str):
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

    def push(self, remote_url: str, credentials):
        remote = self.repository.remotes['origin']

        if not remote:
            remote = self.repository.remotes.create('origin', remote_url)

        callbacks = pygit2.RemoteCallbacks(credentials=credentials)

        remote.push(["refs/heads/main"], callbacks=callbacks)
