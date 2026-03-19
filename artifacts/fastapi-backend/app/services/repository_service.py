"""RepositoryService: repository lifecycle and local workspace management."""
from __future__ import annotations
from datetime import datetime
from pathlib import Path
from app.db.base import SessionLocal
from app.db.enums import SyncStatus
from app.db.models import Account, AppSetting, Credential, Repository, TemplateSource


class RepositoryService:
    def __init__(self, git_client=None, credential_service=None, template_service=None, session_factory=None):
        from app.git.client import GitClient
        from app.services.credential_service import CredentialService
        from app.services.template_service import TemplateService
        self._git = git_client or GitClient()
        self._creds = credential_service or CredentialService(session_factory=session_factory)
        self._templates = template_service or TemplateService(session_factory=session_factory)
        self._session_factory = session_factory or SessionLocal

    def _get_canonical_path(self, session) -> str:
        setting = session.get(AppSetting, "canonical_repo_path")
        if setting is None:
            return str(Path.home() / ".studentflow" / "canonical")
        return setting.value

    def _get_default_branch(self, session) -> str:
        setting = session.get(AppSetting, "default_branch")
        return setting.value if setting is not None else "main"

    def bootstrap_from_canonical(self, student_id: str, account_id: str, local_path: str, remote_url: str) -> Repository:
        with self._session_factory() as session:
            account = session.get(Account, account_id)
            if account is None or account.student_id != student_id:
                raise ValueError(f"Account {account_id} not found or not owned by student {student_id}")
            credential = session.query(Credential).filter_by(account_id=account_id).first()
            if credential is None:
                raise ValueError(f"No credential configured for account {account_id}")
            canonical_path = self._get_canonical_path(session)
            if not self.validate_local_path(canonical_path):
                raise ValueError(f"Canonical repo not found at {canonical_path}")
            branch = self._get_default_branch(session)
            username = account.username
            secret_ref = credential.secret_ref
            auth_type = credential.secret_kind
            cred_value = self._creds.retrieve(secret_ref)
        self._git.clone(canonical_path, local_path, credential=None)
        self._git.add_remote(local_path, "student", remote_url)
        self._git.push(local_path, "student", branch, cred_value, auth_type)
        commit_hash = self._git.get_commit_hash(local_path)
        with self._session_factory() as session:
            repo = Repository(
                account_id=account_id,
                repo_name=f"{username}-project",
                remote_url=remote_url,
                local_path=local_path,
                default_branch=branch,
                integration_branch=branch,
                sync_status=SyncStatus.clean.value,
                last_commit_hash=commit_hash,
                template_source_id=None,
                is_canonical=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            session.add(repo)
            session.commit()
            session.refresh(repo)
            return repo

    def register_existing(self, account_id: str, repo_name: str, remote_url: str, local_path: str,
                           default_branch: str = "main", is_canonical: bool = False) -> Repository:
        with self._session_factory() as session:
            repo = Repository(
                account_id=account_id,
                repo_name=repo_name,
                remote_url=remote_url,
                local_path=local_path,
                default_branch=default_branch,
                integration_branch=default_branch,
                sync_status=SyncStatus.uninitialized.value,
                is_canonical=is_canonical,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            session.add(repo)
            session.commit()
            session.refresh(repo)
            session.expunge(repo)
            return repo

    def validate_local_path(self, path: str) -> bool:
        repo_path = Path(path)
        if not repo_path.exists() or not repo_path.is_dir():
            return False
        return (repo_path / ".git").exists() or (repo_path / "HEAD").exists()

    def validate_remote(self, repo_id: str) -> bool:
        with self._session_factory() as session:
            repo = session.get(Repository, repo_id)
            if repo is None:
                return False
            credential = session.query(Credential).filter_by(account_id=repo.account_id).first()
            if credential is None:
                return False
            try:
                cred_value = self._creds.retrieve(credential.secret_ref)
                return bool(self._git.validate_remote(repo.remote_url, cred_value, credential.secret_kind))
            except Exception:
                return False

    def get_repo_status(self, repo_id: str) -> SyncStatus:
        with self._session_factory() as session:
            repo = session.get(Repository, repo_id)
            if repo is None:
                raise ValueError(f"Repository {repo_id} not found")
            return SyncStatus(repo.sync_status)

    def get_canonical_repo(self) -> Repository | None:
        with self._session_factory() as session:
            repo = session.query(Repository).filter_by(is_canonical=True).first()
            if repo:
                session.expunge(repo)
            return repo

    def list_repos_for_student(self, student_id: str) -> list[Repository]:
        with self._session_factory() as session:
            repos = (
                session.query(Repository)
                .join(Account, Repository.account_id == Account.id)
                .filter(Account.student_id == student_id)
                .all()
            )
            for r in repos:
                session.expunge(r)
            return repos

    def list_all(self) -> list[Repository]:
        with self._session_factory() as session:
            repos = session.query(Repository).all()
            for r in repos:
                session.expunge(r)
            return repos

    def get(self, repo_id: str) -> Repository | None:
        with self._session_factory() as session:
            repo = session.get(Repository, repo_id)
            if repo:
                session.expunge(repo)
            return repo

    def update_sync_status(self, repo_id: str, status: SyncStatus, commit_hash: str | None = None) -> None:
        with self._session_factory() as session:
            repo = session.get(Repository, repo_id)
            if repo is None:
                raise ValueError(f"Repository {repo_id} not found")
            repo.sync_status = status.value if isinstance(status, SyncStatus) else status
            if commit_hash is not None:
                repo.last_commit_hash = commit_hash
            repo.updated_at = datetime.utcnow()
            session.commit()
