"""GitClient: all Git operations via GitPython and subprocess fallback."""
from __future__ import annotations
import os
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlparse
from git import InvalidGitRepositoryError, NoSuchPathError, Repo
from git.exc import BadName, GitCommandError


class GitOperationError(Exception):
    """Raised when a git operation fails."""


class GitMergeError(GitOperationError):
    """Raised when a fast-forward merge fails."""


class GitMergeConflictError(GitOperationError):
    """Raised when a merge produces conflicts."""


class GitAuthError(GitOperationError):
    """Raised when a git operation fails due to authentication."""


class GitClient:
    def __init__(self, timeout: int = 60):
        self._timeout = timeout

    def clone(self, remote_url: str, local_path: str, credential: str | None = None,
              auth_type: str | None = None, ssh_key_path: str | None = None) -> None:
        cmd = ["git", "clone", remote_url, local_path]
        try:
            if credential and auth_type:
                self._run_with_credential(cmd, remote_url=remote_url, credential=credential,
                                          auth_type=auth_type, ssh_key_path=ssh_key_path)
            else:
                self._run_command(cmd)
        except GitOperationError:
            raise
        except Exception as exc:
            raise GitOperationError(f"clone failed for {remote_url}") from exc

    def fetch(self, repo_path: str, remote_name: str = "student") -> None:
        self._run_command(["git", "-C", repo_path, "fetch", remote_name])

    def merge_ff_only(self, repo_path: str, branch: str) -> None:
        try:
            self._run_command(["git", "-C", repo_path, "merge", "--ff-only", branch])
        except GitOperationError as exc:
            raise GitMergeError(f"ff-only merge failed for {branch}") from exc

    def merge_no_ff(self, repo_path: str, branch: str, message: str) -> None:
        try:
            result = subprocess.run(
                ["git", "-C", repo_path, "merge", "--no-ff", branch, "-m", message],
                capture_output=True, text=True, timeout=self._timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise GitMergeConflictError("merge timed out") from exc
        if result.returncode == 0:
            return
        stderr = (result.stderr or "").lower()
        stdout = (result.stdout or "").lower()
        if "conflict" in stderr or "conflict" in stdout:
            raise GitMergeConflictError(f"merge conflict while merging {branch}")
        raise GitOperationError(f"merge failed for {branch}: {self._clean_error_text(result.stderr)}")

    def push(self, repo_path: str, remote_name: str, branch: str, credential: str | None = None,
             auth_type: str | None = None, ssh_key_path: str | None = None, force: bool = False) -> None:
        cmd = ["git", "-C", repo_path, "push"]
        if force:
            cmd.append("--force")
        cmd.extend([remote_name, branch])
        if credential and auth_type:
            remote_url = self._get_remote_url(repo_path, remote_name)
            self._run_with_credential(cmd, remote_url=remote_url, credential=credential,
                                      auth_type=auth_type, ssh_key_path=ssh_key_path)
            return
        self._run_command(cmd)

    def push_to_url(self, repo_path: str, remote_url: str, branch: str, credential: str | None = None,
                    auth_type: str | None = None, force: bool = False) -> None:
        cmd = ["git", "-C", repo_path, "push"]
        if force:
            cmd.append("--force")
        cmd.extend([remote_url, branch])
        if credential and auth_type:
            self._run_with_credential(cmd, remote_url=remote_url, credential=credential, auth_type=auth_type)
            return
        self._run_command(cmd)

    def add_remote(self, repo_path: str, remote_name: str, remote_url: str) -> None:
        repo = self._open_repo(repo_path)
        try:
            repo.create_remote(remote_name, remote_url)
        except GitCommandError as exc:
            raise GitOperationError(f"add remote failed for {remote_name}") from exc

    def create_tag(self, repo_path: str, tag_name: str, message: str | None = None) -> None:
        repo = self._open_repo(repo_path)
        try:
            if message:
                repo.create_tag(tag_name, message=message)
            else:
                repo.create_tag(tag_name)
        except GitCommandError as exc:
            raise GitOperationError(f"create tag failed for {tag_name}") from exc

    def get_commit_hash(self, repo_path: str, ref: str = "HEAD") -> str:
        repo = self._open_repo(repo_path, value_error=True)
        try:
            return repo.commit(ref).hexsha
        except (BadName, ValueError, GitCommandError) as exc:
            raise ValueError(f"Unknown git ref: {ref}") from exc

    def check_divergence(self, repo_path: str, remote_branch: str) -> tuple[int, int]:
        ahead_result = subprocess.run(
            ["git", "-C", repo_path, "rev-list", "--count", f"HEAD..{remote_branch}"],
            capture_output=True, text=True, timeout=self._timeout,
        )
        behind_result = subprocess.run(
            ["git", "-C", repo_path, "rev-list", "--count", f"{remote_branch}..HEAD"],
            capture_output=True, text=True, timeout=self._timeout,
        )
        if ahead_result.returncode != 0 or behind_result.returncode != 0:
            error_text = ahead_result.stderr or behind_result.stderr or "unknown git error"
            raise GitOperationError(f"check_divergence failed: {self._clean_error_text(error_text)}")
        ahead = int(ahead_result.stdout.strip())
        behind = int(behind_result.stdout.strip())
        return ahead, behind

    def init_from_dir(self, src_path: str, dest_path: str) -> None:
        shutil.copytree(src_path, dest_path)
        self._run_command(["git", "init", dest_path])
        self._run_command(["git", "-C", dest_path, "config", "user.email", "studentflow@example.invalid"])
        self._run_command(["git", "-C", dest_path, "config", "user.name", "StudentFlow"])
        self._run_command(["git", "-C", dest_path, "add", "."])
        self._run_command(["git", "-C", dest_path, "commit", "-m", "Initial project template"])

    def validate_remote(self, remote_url: str, credential: str | None = None,
                        auth_type: str | None = None, ssh_key_path: str | None = None) -> bool:
        try:
            cmd = ["git", "ls-remote", remote_url]
            if credential and auth_type:
                self._run_with_credential(cmd, remote_url=remote_url, credential=credential,
                                          auth_type=auth_type, ssh_key_path=ssh_key_path)
            else:
                self._run_command(cmd)
            return True
        except GitOperationError:
            return False

    def reset_hard(self, repo_path: str, ref: str = "HEAD") -> None:
        self._run_command(["git", "-C", repo_path, "reset", "--hard", ref])

    def get_log(self, repo_path: str, limit: int = 10) -> list[dict]:
        repo = self._open_repo(repo_path)
        commits = []
        for commit in repo.iter_commits(max_count=limit):
            commits.append({
                "hash": commit.hexsha,
                "message": commit.message.strip(),
                "author": str(commit.author),
                "date": commit.committed_datetime.isoformat(),
            })
        return commits

    def add_file(self, repo_path: str, file_path: str) -> None:
        self._run_command(["git", "-C", repo_path, "add", "--", file_path])

    def commit(self, repo_path: str, message: str) -> str:
        self._run_command(["git", "-C", repo_path, "commit", "-m", message])
        result = self._run_command(["git", "-C", repo_path, "rev-parse", "HEAD"])
        return result.stdout.strip()

    def _make_netrc_env(self, remote_url: str, credential: str, username: str = "git") -> tuple[dict, str]:
        host = urlparse(remote_url).hostname or "github.com"
        netrc_content = f"machine {host}\nlogin {username}\npassword {credential}\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".netrc", delete=False, encoding="utf-8") as handle:
            handle.write(netrc_content)
            temp_path = handle.name
        os.chmod(temp_path, stat.S_IRUSR | stat.S_IWUSR)
        env = {
            **os.environ,
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "credential.helper",
            "GIT_CONFIG_VALUE_0": f"store --file {temp_path}",
            "HOME": str(Path.home()),
        }
        return env, temp_path

    def _run_with_credential(self, cmd: list[str], remote_url: str, credential: str,
                              auth_type: str, ssh_key_path: str | None = None) -> subprocess.CompletedProcess:
        if auth_type == "ssh":
            env = {
                **os.environ,
                "GIT_SSH_COMMAND": (
                    f"ssh -i {ssh_key_path} -o StrictHostKeyChecking=no -o BatchMode=yes"
                    if ssh_key_path
                    else "ssh -o StrictHostKeyChecking=no -o BatchMode=yes"
                ),
            }
            return self._run_command(cmd, env=env)
        if auth_type in {"pat", "app_password", "password"}:
            env, temp_path = self._make_netrc_env(remote_url, credential)
            try:
                return self._run_command(cmd, env=env)
            finally:
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
        return self._run_command(cmd)

    def _run_command(self, cmd: list[str], *, env: dict | None = None) -> subprocess.CompletedProcess:
        try:
            return subprocess.run(
                cmd, capture_output=True, text=True, timeout=self._timeout, check=True, env=env,
            )
        except subprocess.TimeoutExpired as exc:
            raise GitOperationError(f"git command timed out after {self._timeout}s") from exc
        except subprocess.CalledProcessError as exc:
            raise self._classify_process_error(exc) from exc

    def _classify_process_error(self, exc: subprocess.CalledProcessError) -> GitOperationError:
        message = self._clean_error_text(exc.stderr or exc.stdout or "git command failed")
        lowered = message.lower()
        if any(t in lowered for t in ("authentication failed", "permission denied", "could not read", "access denied")):
            return GitAuthError(message)
        return GitOperationError(message)

    def _get_remote_url(self, repo_path: str, remote_name: str) -> str:
        result = self._run_command(["git", "-C", repo_path, "remote", "get-url", remote_name])
        return result.stdout.strip()

    def _open_repo(self, repo_path: str, *, value_error: bool = False) -> Repo:
        try:
            return Repo(repo_path)
        except (InvalidGitRepositoryError, NoSuchPathError) as exc:
            if value_error:
                raise ValueError(f"Not a git repository: {repo_path}") from exc
            raise GitOperationError(f"Not a git repository: {repo_path}") from exc

    @staticmethod
    def _clean_error_text(text: str | None) -> str:
        return (text or "").strip() or "git command failed"
