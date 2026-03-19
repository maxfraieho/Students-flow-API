"""GitValidator: filesystem and URL validation. No git operations."""
import re
from pathlib import Path

_SSH_PATTERN = re.compile(r'^git@[\w\.\-]+:[\w\.\-/]+\.git$')
_HTTPS_PATTERN = re.compile(r'^https?://[\w\.\-]+(:\d+)?/[\w\.\-/]+\.git$')
_HTTPS_NO_SUFFIX = re.compile(r'^https?://[\w\.\-]+(:\d+)?/[\w\.\-/]+$')
_BAD_BRANCH = re.compile(r'\.\.| |@\{|[\\:?*\[\]^~]')


class GitValidator:
    @staticmethod
    def validate_local_path(path: str) -> Path:
        p = Path(path)
        if not p.exists():
            raise ValueError(f"Path does not exist: {path}")
        if not p.is_dir():
            raise ValueError(f"Path is not a directory: {path}")
        return p.resolve()

    @staticmethod
    def validate_remote_url(url: str) -> str:
        if _SSH_PATTERN.match(url) or _HTTPS_PATTERN.match(url) or _HTTPS_NO_SUFFIX.match(url):
            return url
        raise ValueError(f"Invalid remote URL format: {url}")

    @staticmethod
    def is_git_repo(path) -> bool:
        p = Path(path)
        return (p / ".git").exists() or (p / "HEAD").exists()

    @staticmethod
    def validate_branch_name(branch: str) -> str:
        if not branch:
            raise ValueError("Branch name must not be empty")
        if branch.startswith("/") or branch.endswith("/"):
            raise ValueError(f"Branch name must not start or end with '/': {branch}")
        if _BAD_BRANCH.search(branch):
            raise ValueError(f"Branch name contains invalid characters: {branch}")
        return branch
