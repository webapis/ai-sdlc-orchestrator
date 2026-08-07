"""
GitHub implementation of VcsAdapter. See docs/architecture.md §11.1.
"""

from .base import VcsAdapter, PullRequestRef


class GitHubAdapter(VcsAdapter):
    def __init__(self, token: str):
        self._token = token
        # TODO: initialize a GitHub API client

    def create_branch(self, project, base, name):
        raise NotImplementedError

    def create_pull_request(self, project, branch, title, body) -> PullRequestRef:
        raise NotImplementedError

    def post_status(self, project, ref, state, description):
        raise NotImplementedError

    def read_file(self, project, path, ref) -> str:
        raise NotImplementedError
