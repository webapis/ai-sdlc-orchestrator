"""
Provider-agnostic VCS interface. See docs/architecture.md §11.1.
Workflow specs reference only `vcs_provider` at the project level;
node code should depend on this protocol, never on a concrete adapter.
"""

from typing import Protocol


class PullRequestRef:
    def __init__(self, url: str, number: int):
        self.url = url
        self.number = number


class VcsAdapter(Protocol):
    def create_branch(self, project, base: str, name: str) -> None: ...

    def create_pull_request(
        self, project, branch: str, title: str, body: str
    ) -> PullRequestRef: ...

    def post_status(self, project, ref: str, state: str, description: str) -> None: ...

    def read_file(self, project, path: str, ref: str) -> str: ...
