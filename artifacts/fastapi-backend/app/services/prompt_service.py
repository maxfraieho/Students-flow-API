"""PromptService: create, commit, and push prompt files for the active student."""
from __future__ import annotations
import re
from datetime import datetime
from pathlib import Path
from app.db.base import SessionLocal
from app.db.enums import PromptStatus, StudentStatus
from app.db.models import Account, Credential, Prompt, Repository, Student


def _make_slug(title: str) -> str:
    if not title or not title.strip():
        return "prompt"
    s = title.lower().strip()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"[\s-]+", "-", s)
    s = s.strip("-")
    return s[:40] or "prompt"


def _make_file_path(student_number: int, seq_number: int, slug: str) -> str:
    return f"prompts/student{student_number:02d}-{seq_number:03d}-{slug}.md"


def _make_file_content(title: str, student_number: int, seq_number: int, created_by: str,
                        repo_name: str, branch: str, prompt_text: str, created_at: datetime) -> str:
    display_title = title.strip() or "Prompt"
    ts = created_at.strftime("%Y-%m-%d %H:%M:%S UTC")
    return (
        f"# {display_title}\n\n"
        f"| Field | Value |\n"
        f"|---|---|\n"
        f"| Student | #{student_number:02d} |\n"
        f"| Sequence | {seq_number:03d} |\n"
        f"| Created at | {ts} |\n"
        f"| Created by | {created_by} |\n"
        f"| Target repo | {repo_name} |\n"
        f"| Target branch | {branch} |\n"
        f"\n## Prompt\n\n{prompt_text}\n"
    )


def _sanitize_error(message: str) -> str:
    cleaned = re.sub(r"ghp_[A-Za-z0-9]{20,}", "[token]", message)
    cleaned = re.sub(r"glpat-[A-Za-z0-9\-_]{10,}", "[token]", cleaned)
    cleaned = re.sub(r"github_pat_[A-Za-z0-9_]{20,}", "[token]", cleaned)
    return cleaned[:280]


class PromptService:
    def __init__(self, git_client=None, credential_service=None, audit_service=None, session_factory=None):
        from app.git.client import GitClient
        from app.services.audit_service import AuditService
        from app.services.credential_service import CredentialService
        self._git = git_client or GitClient()
        self._creds = credential_service or CredentialService(session_factory=session_factory)
        self._audit = audit_service or AuditService(session_factory=session_factory)
        self._session_factory = session_factory or SessionLocal

    def _get_active_student(self, session) -> Student:
        student = (
            session.query(Student)
            .filter(Student.status == StudentStatus.active.value)
            .order_by(Student.queue_position.asc(), Student.created_at.asc())
            .first()
        )
        if student is None:
            raise ValueError("No active student found")
        return student

    def _get_student_repo(self, session, student_id: str) -> tuple[Repository, Credential]:
        account = (
            session.query(Account).filter_by(student_id=student_id, is_current=True).first()
            or session.query(Account).filter_by(student_id=student_id).first()
        )
        if account is None:
            raise ValueError(f"No account for student {student_id}")
        repo = session.query(Repository).filter_by(account_id=account.id, is_canonical=False).first()
        if repo is None:
            raise ValueError(f"No repository for student {student_id}")
        cred = session.query(Credential).filter_by(account_id=account.id).first()
        if cred is None:
            raise ValueError(f"No credential for account {account.id}")
        return repo, cred

    def _next_seq(self, session, student_id: str) -> int:
        from sqlalchemy import func
        result = session.query(func.max(Prompt.seq_number)).filter(Prompt.student_id == student_id).scalar()
        return (result or 0) + 1

    def create_and_push_prompt(self, title: str, content: str, created_by: str = "operator") -> Prompt:
        with self._session_factory() as session:
            student = self._get_active_student(session)
            repo, cred = self._get_student_repo(session, student.id)
            student_number = student.student_number
            if student_number is None:
                raise ValueError(f"Student {student.full_name!r} has no student_number assigned.")
            seq_number = self._next_seq(session, student.id)
            slug = _make_slug(title)
            file_path = _make_file_path(student_number, seq_number, slug)
            branch = repo.default_branch or "main"
            created_at = datetime.utcnow()
            file_content = _make_file_content(
                title=title, student_number=student_number, seq_number=seq_number,
                created_by=created_by, repo_name=repo.repo_name, branch=branch,
                prompt_text=content, created_at=created_at,
            )
            prompt = Prompt(
                student_id=student.id,
                repository_id=repo.id,
                student_number=student_number,
                seq_number=seq_number,
                title=title.strip(),
                slug=slug,
                content=content,
                file_path=file_path,
                git_branch=branch,
                status=PromptStatus.draft.value,
                created_by=created_by,
                created_at=created_at,
            )
            session.add(prompt)
            session.commit()
            session.refresh(prompt)
            prompt_id = prompt.id
            local_path = repo.local_path
            secret_ref = cred.secret_ref
            auth_type = cred.secret_kind

        abs_file = Path(local_path) / file_path
        abs_file.parent.mkdir(parents=True, exist_ok=True)
        abs_file.write_text(file_content, encoding="utf-8")

        with self._session_factory() as session:
            p = session.get(Prompt, prompt_id)
            p.status = PromptStatus.written.value
            session.commit()

        try:
            self._git.add_file(local_path, file_path)
        except Exception as exc:
            with self._session_factory() as session:
                p = session.get(Prompt, prompt_id)
                p.status = PromptStatus.failed.value
                p.push_error = _sanitize_error(str(exc))
                session.commit()
                session.refresh(p)
                session.expunge(p)
            return p

        commit_hash: str | None = None
        try:
            commit_msg = f"prompt: {Path(file_path).stem}"
            commit_hash = self._git.commit(local_path, commit_msg)
        except Exception as exc:
            with self._session_factory() as session:
                p = session.get(Prompt, prompt_id)
                p.status = PromptStatus.failed.value
                p.push_error = _sanitize_error(str(exc))
                session.commit()
                session.refresh(p)
                session.expunge(p)
            return p

        with self._session_factory() as session:
            p = session.get(Prompt, prompt_id)
            p.status = PromptStatus.committed.value
            p.git_commit_hash = commit_hash
            session.commit()
        self._audit.log("prompt_committed", "prompt", prompt_id,
                        details={"file_path": file_path, "commit_hash": commit_hash})

        try:
            credential_value = self._creds.retrieve(secret_ref)
            self._git.push(local_path, "student", branch, credential=credential_value, auth_type=auth_type)
        except Exception as exc:
            with self._session_factory() as session:
                p = session.get(Prompt, prompt_id)
                p.status = PromptStatus.failed.value
                p.push_error = _sanitize_error(str(exc))
                session.commit()
                session.expunge(p)
            self._audit.log("prompt_push_failed", "prompt", prompt_id,
                            details={"file_path": file_path, "error": _sanitize_error(str(exc))})
            return p

        with self._session_factory() as session:
            p = session.get(Prompt, prompt_id)
            p.status = PromptStatus.pushed.value
            p.pushed_at = datetime.utcnow()
            session.commit()
            session.refresh(p)
            session.expunge(p)
        self._audit.log("prompt_pushed", "prompt", prompt_id,
                        details={"file_path": file_path, "student_number": student_number})
        return p

    def retry_push(self, prompt_id: str) -> Prompt:
        with self._session_factory() as session:
            prompt = session.get(Prompt, prompt_id)
            if prompt is None:
                raise ValueError(f"Prompt {prompt_id} not found")
            if prompt.status not in (PromptStatus.failed.value, PromptStatus.committed.value):
                raise ValueError(f"Prompt {prompt_id} is not in a retryable state")
            repo, cred = self._get_student_repo(session, prompt.student_id)
            local_path = repo.local_path
            branch = prompt.git_branch
            secret_ref = cred.secret_ref
            auth_type = cred.secret_kind
            file_path = prompt.file_path
        try:
            credential_value = self._creds.retrieve(secret_ref)
            self._git.push(local_path, "student", branch, credential=credential_value, auth_type=auth_type)
        except Exception as exc:
            with self._session_factory() as session:
                p = session.get(Prompt, prompt_id)
                p.status = PromptStatus.failed.value
                p.push_error = _sanitize_error(str(exc))
                session.commit()
                session.expunge(p)
            return p

        with self._session_factory() as session:
            p = session.get(Prompt, prompt_id)
            p.status = PromptStatus.pushed.value
            p.pushed_at = datetime.utcnow()
            p.push_error = None
            session.commit()
            session.expunge(p)
        self._audit.log("prompt_pushed", "prompt", prompt_id, details={"retry": True})
        return p

    def list_prompts(self, student_id: str | None = None) -> list[Prompt]:
        with self._session_factory() as session:
            q = session.query(Prompt).order_by(Prompt.created_at.desc())
            if student_id is not None:
                q = q.filter(Prompt.student_id == student_id)
            prompts = q.all()
            session.expunge_all()
            return prompts

    def get(self, prompt_id: str) -> Prompt | None:
        with self._session_factory() as session:
            p = session.get(Prompt, prompt_id)
            if p:
                session.expunge(p)
            return p
