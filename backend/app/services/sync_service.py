"""SyncService: pull canonical → student repo, update DB status."""
from __future__ import annotations
import json
from datetime import datetime
from typing import Generator
import structlog
from app.db.base import SessionLocal
from app.db.enums import SyncJobStatus, SyncJobType, SyncStatus, StudentStatus
from app.db.models import Account, Credential, Repository, Student, SyncJob

logger = structlog.get_logger(__name__)


class SyncError(Exception):
    pass


class SyncService:
    def __init__(self, git_client=None, credential_service=None, audit_service=None, session_factory=None):
        from app.git.client import GitClient
        from app.services.audit_service import AuditService
        from app.services.credential_service import CredentialService
        self._git = git_client or GitClient()
        self._creds = credential_service or CredentialService(session_factory=session_factory)
        self._audit = audit_service or AuditService(session_factory=session_factory)
        self._session_factory = session_factory or SessionLocal

    # ------------------------------------------------------------------
    # Broadcast canonical → all active student repos (streaming)
    # ------------------------------------------------------------------

    def broadcast_canonical_stream(self) -> Generator[str, None, None]:
        """
        Sync generator yielding SSE-formatted progress lines.

        Each yielded string is a complete SSE event:
            data: {...JSON...}\\n\\n

        Flow:
          1. Fetch latest into local canonical repo.
          2. Collect all active students (with repo + credential).
          3. For every student: hard-reset local clone to canonical HEAD,
             then git push --force to their remote.
        """

        # ── Step 1: locate canonical repo ─────────────────────────────
        with self._session_factory() as session:
            canonical_repo = (
                session.query(Repository)
                .filter_by(is_canonical=True)
                .first()
            )
            if canonical_repo is None:
                yield _sse({"event": "error", "message": "No canonical repository configured"})
                return
            canonical_path = canonical_repo.local_path
            canonical_branch = canonical_repo.default_branch

        # ── Step 2: pull latest into canonical repo ───────────────────
        try:
            self._git.fetch(canonical_path, "origin")
            self._git.reset_hard(canonical_path, f"origin/{canonical_branch}")
            yield _sse({"event": "canonical_pulled", "branch": canonical_branch, "status": "ok"})
        except Exception as exc:
            yield _sse({"event": "canonical_pulled", "status": "error", "error": str(exc)[:300]})
            return

        # ── Step 3: collect active students ───────────────────────────
        with self._session_factory() as session:
            students = (
                session.query(Student)
                .filter(Student.status == StudentStatus.active.value)
                .order_by(Student.queue_position.asc(), Student.created_at.asc())
                .all()
            )
            rows: list[dict] = []
            for student in students:
                account = (
                    session.query(Account)
                    .filter_by(student_id=student.id, is_current=True)
                    .first()
                ) or session.query(Account).filter_by(student_id=student.id).first()

                if account is None:
                    continue
                repo = (
                    session.query(Repository)
                    .filter_by(account_id=account.id, is_canonical=False)
                    .first()
                )
                credential = (
                    session.query(Credential)
                    .filter_by(account_id=account.id)
                    .first()
                )
                if repo is None or credential is None:
                    continue
                rows.append({
                    "student_id": student.id,
                    "full_name": student.full_name,
                    "repo_id": repo.id,
                    "local_path": repo.local_path,
                    "branch": repo.default_branch,
                    "secret_ref": credential.secret_ref,
                    "auth_type": credential.secret_kind,
                })

        total = len(rows)
        yield _sse({"event": "broadcast_start", "total": total})

        # ── Step 4: process each student ──────────────────────────────
        succeeded = 0
        failed = 0
        for idx, row in enumerate(rows, 1):
            name = row["full_name"]
            yield _sse({"event": "processing", "student": name, "index": idx, "total": total})
            try:
                pat = self._creds.retrieve(row["secret_ref"])
                local_path = row["local_path"]
                branch = row["branch"]

                # Ensure 'canonical' remote points at our local canonical clone
                self._git.ensure_remote(local_path, "canonical", canonical_path)

                # Hard-reset local clone to canonical HEAD
                self._git.fetch(local_path, "canonical")
                self._git.reset_hard(local_path, f"canonical/{canonical_branch}")

                # Force-push to the student's GitHub remote
                self._git.push(
                    local_path,
                    remote_name="student",
                    branch=branch,
                    credential=pat,
                    auth_type=row["auth_type"],
                    force=True,
                )

                hash_after = self._git.get_commit_hash(local_path)
                self.update_repo_status(row["repo_id"], SyncStatus.clean, hash_after)
                succeeded += 1
                yield _sse({
                    "event": "done",
                    "student": name,
                    "index": idx,
                    "status": "success",
                    "commit": hash_after[:8],
                })
            except Exception as exc:
                failed += 1
                self.update_repo_status(row["repo_id"], SyncStatus.error)
                logger.warning("broadcast_student_failed", student=name, error=str(exc))
                yield _sse({
                    "event": "done",
                    "student": name,
                    "index": idx,
                    "status": "error",
                    "error": str(exc)[:300],
                })

        yield _sse({
            "event": "broadcast_complete",
            "total": total,
            "succeeded": succeeded,
            "failed": failed,
        })

    # ------------------------------------------------------------------
    # Existing sync methods
    # ------------------------------------------------------------------

    def sync_current_student(self) -> SyncJob:
        with self._session_factory() as session:
            student = (
                session.query(Student)
                .filter(Student.status == StudentStatus.active.value)
                .order_by(Student.queue_position.asc(), Student.created_at.asc())
                .first()
            )
            if student is None:
                raise SyncError("No active student found")
            student_id = student.id
            account = (
                session.query(Account).filter_by(student_id=student_id, is_current=True).first()
                or session.query(Account).filter_by(student_id=student_id).first()
            )
            if account is None:
                raise SyncError(f"No account for student {student_id}")
            repo = session.query(Repository).filter_by(account_id=account.id, is_canonical=False).first()
            if repo is None:
                raise SyncError(f"No repository for student {student_id}")
            credential = session.query(Credential).filter_by(account_id=account.id).first()
            if credential is None:
                raise SyncError(f"No credential for account {account.id}")
            repo_id = repo.id
            local_path = repo.local_path
            branch = repo.default_branch
            hash_before = repo.last_commit_hash
            job = SyncJob(
                repo_id=repo_id,
                student_id=student_id,
                job_type=SyncJobType.sync_current.value,
                status=SyncJobStatus.running.value,
                started_at=datetime.utcnow(),
                commit_hash_before=hash_before,
                created_at=datetime.utcnow(),
            )
            session.add(job)
            session.commit()
            session.refresh(job)
            job_id = job.id

        try:
            self._git.fetch(local_path, "student")
            self._git.merge_ff_only(local_path, f"student/{branch}")
            hash_after = self._git.get_commit_hash(local_path)
        except Exception as exc:
            with self._session_factory() as session:
                j = session.get(SyncJob, job_id)
                j.status = SyncJobStatus.failed.value
                j.finished_at = datetime.utcnow()
                j.error_message = str(exc)[:500]
                session.commit()
                session.expunge(j)
            self.update_repo_status(repo_id, SyncStatus.error)
            raise SyncError(str(exc)) from exc

        with self._session_factory() as session:
            j = session.get(SyncJob, job_id)
            j.status = SyncJobStatus.success.value
            j.finished_at = datetime.utcnow()
            j.commit_hash_after = hash_after
            j.summary = f"Synced to {hash_after[:8]}"
            session.commit()
            session.refresh(j)
            session.expunge(j)

        self.update_repo_status(repo_id, SyncStatus.clean, hash_after)
        self._audit.log("sync_completed", "sync_job", job_id,
                        details={"repo_id": repo_id, "student_id": student_id, "hash": hash_after})
        return j

    def sync_student(self, student_id: str) -> SyncJob:
        with self._session_factory() as session:
            account = (
                session.query(Account).filter_by(student_id=student_id, is_current=True).first()
                or session.query(Account).filter_by(student_id=student_id).first()
            )
            if account is None:
                raise SyncError(f"No account for student {student_id}")
            repo = session.query(Repository).filter_by(account_id=account.id, is_canonical=False).first()
            if repo is None:
                raise SyncError(f"No repository for student {student_id}")
            credential = session.query(Credential).filter_by(account_id=account.id).first()
            if credential is None:
                raise SyncError(f"No credential for account {account.id}")
            repo_id = repo.id
            local_path = repo.local_path
            branch = repo.default_branch
            hash_before = repo.last_commit_hash
            job = SyncJob(
                repo_id=repo_id,
                student_id=student_id,
                job_type=SyncJobType.sync_current.value,
                status=SyncJobStatus.running.value,
                started_at=datetime.utcnow(),
                commit_hash_before=hash_before,
                created_at=datetime.utcnow(),
            )
            session.add(job)
            session.commit()
            session.refresh(job)
            job_id = job.id

        try:
            self._git.fetch(local_path, "student")
            self._git.merge_ff_only(local_path, f"student/{branch}")
            hash_after = self._git.get_commit_hash(local_path)
        except Exception as exc:
            with self._session_factory() as session:
                j = session.get(SyncJob, job_id)
                j.status = SyncJobStatus.failed.value
                j.finished_at = datetime.utcnow()
                j.error_message = str(exc)[:500]
                session.commit()
                session.expunge(j)
            self.update_repo_status(repo_id, SyncStatus.error)
            raise SyncError(str(exc)) from exc

        with self._session_factory() as session:
            j = session.get(SyncJob, job_id)
            j.status = SyncJobStatus.success.value
            j.finished_at = datetime.utcnow()
            j.commit_hash_after = hash_after
            j.summary = f"Synced to {hash_after[:8]}"
            session.commit()
            session.expunge(j)

        self.update_repo_status(repo_id, SyncStatus.clean, hash_after)
        return j

    def list_jobs(self, student_id: str | None = None, limit: int = 50) -> list[SyncJob]:
        with self._session_factory() as session:
            q = session.query(SyncJob).order_by(SyncJob.created_at.desc()).limit(limit)
            if student_id:
                q = (
                    session.query(SyncJob)
                    .filter_by(student_id=student_id)
                    .order_by(SyncJob.created_at.desc())
                    .limit(limit)
                )
            jobs = q.all()
            for j in jobs:
                session.expunge(j)
            return jobs

    def update_repo_status(
        self, repo_id: str, status: SyncStatus, commit_hash: str | None = None
    ) -> None:
        with self._session_factory() as session:
            repo = session.get(Repository, repo_id)
            if repo is None:
                return
            repo.sync_status = status.value
            if commit_hash:
                repo.last_commit_hash = commit_hash
            repo.updated_at = datetime.utcnow()
            session.commit()


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _sse(payload: dict) -> str:
    """Format a dict as a single Server-Sent Events data line."""
    return f"data: {json.dumps(payload)}\n\n"
