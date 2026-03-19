"""HandoffService: orchestrates the full student handoff process."""
from __future__ import annotations
from datetime import datetime
import re
import structlog
from app.db.base import SessionLocal
from app.db.enums import HandoffStatus, StudentStatus
from app.db.models import Account, AppSetting, Credential, HandoffEvent, Repository, Student

logger = structlog.get_logger(__name__)


class HandoffError(Exception):
    pass


class NoActiveStudentError(HandoffError):
    pass


class NoNextStudentError(HandoffError):
    pass


def _build_checkpoint_tag(student_name: str, commit_hash: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", student_name.lower().strip()).strip("-")[:30]
    ts = datetime.utcnow().strftime("%Y-%m-%d")
    return f"checkpoint/{slug}/{ts}/{commit_hash[:8]}"


class HandoffService:
    def __init__(self, git_client=None, credential_service=None, audit_service=None, session_factory=None):
        from app.git.client import GitClient
        from app.services.audit_service import AuditService
        from app.services.credential_service import CredentialService
        self._git = git_client or GitClient()
        self._creds = credential_service or CredentialService(session_factory=session_factory)
        self._audit_service = audit_service or AuditService(session_factory=session_factory)
        self._session_factory = session_factory or SessionLocal

    def do_handoff(self) -> HandoffEvent:
        with self._session_factory() as session:
            current = self._get_active_student(session)
            if current is None:
                raise NoActiveStudentError("No active student found")
            next_student = self._get_next_student(session, current.id)
            if next_student is None:
                raise NoNextStudentError(f"No next student found after {current.full_name}")
            account = self._get_student_account(session, current.id)
            repo = self._get_student_repository(session, account.id)
            canonical_path = self._get_canonical_path(session, repo)
            canonical_repo_id = self._get_canonical_repo_id(session, repo)
            credential = session.query(Credential).filter_by(account_id=account.id).first()
            if credential is None:
                raise HandoffError(f"No credential for account {account.id}")
            local_path = repo.local_path
            branch = repo.default_branch
            secret_ref = credential.secret_ref
            auth_type = credential.secret_kind
            current_id = current.id
            next_id = next_student.id
            repo_id = repo.id
            current_name = current.full_name

        try:
            cred_value = self._creds.retrieve(secret_ref)
        except Exception as exc:
            raise HandoffError(f"Could not retrieve credential: {exc}") from exc

        try:
            self._git.fetch(local_path, "student")
            self._git.merge_ff_only(local_path, f"student/{branch}")
        except Exception as exc:
            raise HandoffError(f"Sync before handoff failed: {exc}") from exc

        try:
            commit_hash = self._git.get_commit_hash(local_path)
        except Exception as exc:
            raise HandoffError(f"Could not read commit hash: {exc}") from exc

        checkpoint_tag = _build_checkpoint_tag(current_name, commit_hash)
        try:
            self._git.create_tag(local_path, checkpoint_tag, message=f"Checkpoint for {current_name}")
        except Exception as exc:
            raise HandoffError(f"Tag creation failed: {exc}") from exc

        try:
            merge_message = f"Merge student/{branch} into canonical (handoff {checkpoint_tag})"
            self._git.merge_no_ff(canonical_path, f"../{local_path}", merge_message)
        except Exception:
            try:
                self._git.merge_no_ff(canonical_path, local_path, merge_message)
            except Exception as exc:
                raise HandoffError(f"Canonical merge failed: {exc}") from exc

        event_payload = {
            "id": None,
            "from_student_id": current_id,
            "to_student_id": next_id,
            "repo_id": repo_id,
            "commit_hash": commit_hash,
            "checkpoint_tag": checkpoint_tag,
        }

        with self._session_factory() as session:
            event = HandoffEvent(
                from_student_id=current_id,
                to_student_id=next_id,
                repo_id=repo_id,
                commit_hash=commit_hash,
                checkpoint_tag=checkpoint_tag,
                status=HandoffStatus.completed.value,
                created_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
            )
            session.add(event)
            current_student = session.get(Student, current_id)
            next_student_db = session.get(Student, next_id)
            current_student.status = StudentStatus.exhausted.value
            next_student_db.status = StudentStatus.active.value
            session.commit()
            session.refresh(event)
            session.expunge(event)

        self._audit_service.log(
            "handoff_completed", "handoff_event", event.id,
            details={"checkpoint_tag": checkpoint_tag, "commit_hash": commit_hash,
                     "from": current_id, "to": next_id},
        )
        return event

    def list_events(self, limit: int = 50) -> list[HandoffEvent]:
        with self._session_factory() as session:
            events = (
                session.query(HandoffEvent)
                .order_by(HandoffEvent.created_at.desc())
                .limit(limit)
                .all()
            )
            for e in events:
                session.expunge(e)
            return events

    def get_event(self, event_id: str) -> HandoffEvent | None:
        with self._session_factory() as session:
            e = session.get(HandoffEvent, event_id)
            if e:
                session.expunge(e)
            return e

    def _get_active_student(self, session) -> Student | None:
        return (
            session.query(Student)
            .filter(Student.status == StudentStatus.active.value)
            .order_by(Student.queue_position.asc(), Student.created_at.asc())
            .first()
        )

    def _get_next_student(self, session, current_student_id: str | None) -> Student | None:
        query = session.query(Student).filter(
            Student.status.in_([StudentStatus.active.value, StudentStatus.paused.value]),
        )
        if current_student_id is not None:
            query = query.filter(Student.id != current_student_id)
        return query.order_by(Student.queue_position.asc(), Student.created_at.asc()).first()

    def _get_student_account(self, session, student_id: str) -> Account:
        account = session.query(Account).filter_by(student_id=student_id, is_current=True).first()
        if account is None:
            account = session.query(Account).filter_by(student_id=student_id).order_by(Account.created_at.asc()).first()
        if account is None:
            raise HandoffError(f"No account found for student {student_id}")
        return account

    def _get_student_repository(self, session, account_id: str) -> Repository:
        repo = session.query(Repository).filter_by(account_id=account_id, is_canonical=False).first()
        if repo is None:
            raise HandoffError(f"No repository found for account {account_id}")
        return repo

    def _get_canonical_path(self, session, fallback_repo: Repository) -> str:
        setting = session.get(AppSetting, "canonical_repo_path")
        if setting is not None and setting.value:
            return setting.value
        canonical_repo = session.query(Repository).filter_by(is_canonical=True).first()
        if canonical_repo is not None:
            return canonical_repo.local_path
        return fallback_repo.local_path

    def _get_canonical_repo_id(self, session, fallback_repo: Repository) -> str:
        canonical_repo = session.query(Repository).filter_by(is_canonical=True).first()
        if canonical_repo is not None:
            return canonical_repo.id
        return fallback_repo.id
