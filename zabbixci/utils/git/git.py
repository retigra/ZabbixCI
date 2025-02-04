import logging
import os
from typing import ParamSpec

import pygit2
from pygit2.enums import MergeAnalysis

from zabbixci.settings import Settings
from zabbixci.utils.cache.cache import Cache
from zabbixci.utils.git.credentials import RemoteCallbacksSecured

logger = logging.getLogger(__name__)

P = ParamSpec("P")


class Git:
    _repository: pygit2.Repository = None
    author = pygit2.Signature(Settings.GIT_AUTHOR_NAME, Settings.GIT_AUTHOR_EMAIL)
    _git_cb = None

    def __init__(self, path: str, callbacks: pygit2.RemoteCallbacks):
        """
        Initialize the git repository
        """
        self._git_cb = callbacks

        if not os.path.exists(path):
            Cache.makedirs(path)

            self._repository = pygit2.clone_repository(
                Settings.REMOTE,
                path,
                callbacks=self._git_cb,
            )
        else:
            self._repository = pygit2.Repository(path)

    @property
    def has_changes(self):
        """
        Check if the repository has changes, returns True if there are changes, False otherwise
        """
        return len(self._repository.status()) > 0

    @property
    def ahead_of_remote(self):
        """
        Check if the repository is ahead of the remote repository
        """
        branch = self._repository.head.shorthand
        try:
            remote_id = self._repository.lookup_reference(
                f"refs/remotes/origin/{branch}"
            ).target

            return self._repository.head.target != remote_id
        except KeyError:
            # Remote branch does not exist, we must push our state to the remote
            return True

    @property
    def current_branch(self):
        """
        Get the current branch
        """
        return self._repository.head.shorthand

    @property
    def is_empty(self):
        """
        Check if the repository is empty
        """
        return self._repository.is_empty

    def _mark_agent_active(self):
        if isinstance(self._git_cb, RemoteCallbacksSecured):
            self._git_cb.mark_agent_active()

    def get_current_revision(self):
        """
        Get the current revision
        """
        return self._repository.head.target

    def status(self, *args: P.args, **kwargs: P.kwargs):
        """
        Get the status of the repository
        """
        return self._repository.status(*args, **kwargs)

    def switch_branch(self, branch: str):
        """
        Switch to a branch, if the branch does not exist, create it
        """
        if not self._repository.branches.local.get(branch):
            logger.debug(f"Branch {branch} does not exist, creating")
            self.create_branch(branch)

        local_branch = self._repository.branches.local[branch]

        self._repository.checkout(local_branch)
        self._repository.head.set_target(local_branch.target)
        logger.debug(f"Switched to branch {branch}")

    def create_branch(self, branch: str):
        """
        Create a branch
        """
        try:
            self._repository.branches.local.create(branch, self._repository.head.peel())
        except Exception as e:
            logger.error(f"Failed to create branch: {e}")

    def add_all(self):
        """
        Add all changes to the index
        """
        index = self._repository.index
        index.add_all()
        index.write()

    def reset(self, *args: P.args, **kwargs: P.kwargs):
        """
        Reset the repository
        """
        self._repository.reset(*args, **kwargs)

    def fetch(self, remote_url: str):
        """
        Fetch the changes from the remote repository
        """
        if "origin" not in self._repository.remotes.names():
            self._repository.remotes.create("origin", remote_url)

        remote = self._repository.remotes["origin"]

        remote.fetch(callbacks=self._git_cb)
        self._mark_agent_active()

    def lookup_reference(self, name: str):
        return self._repository.lookup_reference(name)

    def commit(self, message: str):
        """
        Commit current index to the repository
        """
        index = self._repository.index
        index.write()

        tree = index.write_tree()

        self._repository.create_commit(
            "HEAD",
            self.author,
            self.author,
            message,
            tree,
            (
                [self._repository.head.target]
                if not self._repository.head_is_unborn
                else []
            ),
        )

    def clean(self):
        """
        Clean the repository from untracked files
        """
        self._repository.checkout_head(strategy=pygit2.GIT_CHECKOUT_FORCE)
        self._repository.state_cleanup()

        # Any remaining untracked files will be removed
        changes = self._repository.status()

        for file in changes:
            os.remove(f"{self._repository.workdir}/{file}")

    def push(self, remote_url: str, branch: str = None):
        """
        Push the changes to the remote repository
        """
        remote = self._repository.remotes["origin"]

        if not branch:
            branch = self._repository.head.shorthand

        if not remote:
            remote = self._repository.remotes.create("origin", remote_url)

        remote.push([f"refs/heads/{branch}"], callbacks=self._git_cb)
        self._mark_agent_active()

    def force_push(self, specs: list[str], remote_url: str):
        """
        Force push the changes to the remote repository
        """
        remote = self._repository.remotes["origin"]

        if not remote:
            remote = self._repository.remotes.create("origin", remote_url)

        remote.push(specs, callbacks=self._git_cb)
        self._mark_agent_active()

    def pull(self, remote_url: str, branch: str = None):
        """
        Pull the changes from the remote repository, merge them with the local repository
        """
        remote = self._repository.remotes["origin"]

        if not branch:
            branch = self._repository.head.shorthand

        if not remote:
            remote = self._repository.remotes.create("origin", remote_url)

        remote.fetch(callbacks=self._git_cb)

        remote_id = self._repository.lookup_reference(
            f"refs/remotes/origin/{branch}"
        ).target

        merge_result, merge_pref = self._repository.merge_analysis(remote_id)

        if merge_result & MergeAnalysis.UP_TO_DATE:
            logger.debug("Already up to date")
            return

        if merge_result & MergeAnalysis.FASTFORWARD:
            self._repository.checkout_tree(self._repository.get(remote_id))

            try:
                self._repository.head.set_target(remote_id)
            except Exception as e:
                logger.error(f"Failed to fast-forward: {e}")

        if merge_result & MergeAnalysis.NORMAL:
            self._repository.merge(remote_id)

            if self._repository.index.conflicts:
                logger.error("Conflicts detected")
                return

        self._repository.state_cleanup()
        self.commit("Merge changes")
        self._mark_agent_active()
