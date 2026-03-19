"""SyncService: canonical ↔ student sync, job tracking, and broadcast."""
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
    # Context helpers
    # ------------------------------------------------------------------

    def _canonical_context(self) -> dict:
        with self._session_factory() as session:
            repo = session.query(Repository).filter_by(is_canonical=True).first()
            if repo is None:
                raise SyncError("No canonical repository configured")
            return {
                "repo_id": repo.id,
                "local_path": repo.local_path,
                "branch": repo.default_branch,
            }

    def _student_context(self, student_id: str) -> dict:
        with self._session_factory() as session:
            student = session.get(Student, student_id)
            if student is None:
                raise SyncError(f"Student {student_id} not found")

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

            return {
                "student_id": student.id,
                "student_name": student.full_name,
                "repo_id": repo.id,
                "local_path": repo.local_path,
                "branch": repo.default_branch,
                "hash_before": repo.last_commit_hash,
                "secret_ref": credential.secret_ref,
                "auth_type": credential.secret_kind,
            }

    def _create_job(self, *, repo_id: str, student_id: str, job_type: SyncJobType, hash_before: str | None) -> str:
        with self._session_factory() as session:
            job = SyncJob(
                repo_id=repo_id,
                student_id=student_id,
                job_type=job_type.value,
                status=SyncJobStatus.running.value,
                started_at=datetime.utcnow(),
                commit_hash_before=hash_before,
                created_at=datetime.utcnow(),
            )
            session.add(job)
            session.commit()
            session.refresh(job)
            return job.id

    def _fail_job(self, job_id: str, error: Exception) -> None:
        with self._session_factory() as session:
            job = session.get(SyncJob, job_id)
            if job is None:
                return
            job.status = SyncJobStatus.failed.value
            job.finished_at = datetime.utcnow()
            job.error_message = str(error)[:500]
            session.commit()

    def _succeed_job(self, job_id: str, hash_after: str, summary: str) -> SyncJob:
        with self._session_factory() as session:
            job = session.get(SyncJob, job_id)
            if job is None:
                raise SyncError(f"Sync job {job_id} not found")
            job.status = SyncJobStatus.success.value
            job.finished_at = datetime.utcnow()
            job.commit_hash_after = hash_after
            job.summary = summary
            session.commit()
            session.refresh(job)
            session.expunge(job)
            return job

    # ------------------------------------------------------------------
    # Broadcast canonical → all active student repos (streaming)
    # ------------------------------------------------------------------

    def broadcast_canonical_stream(self) -> Generator[str, None, None]:
        with self._session_factory() as session:
            canonical_repo = session.query(Repository).filter_by(is_canonical=True).first()
            if canonical_repo is None:
                yield _sse({"event": "error", "message": "No canonical repository configured"})
                return
            canonical_path = canonical_repo.local_path
            canonical_branch = canonical_repo.default_branch

        try:
            self._git.fetch(canonical_path, "origin")
            self._git.reset_hard(canonical_path, f"origin/{canonical_branch}")
            yield _sse({"event": "canonical_pulled", "branch": canonical_branch, "status": "ok"})
        except Exception as exc:
            yield _sse({"event": "canonical_pulled", "status": "error", "error": str(exc)[:300]})
            return

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

        succeeded = 0
        failed = 0
        for idx, row in enumerate(rows, 1):
            name = row["full_name"]
            yield _sse({"event": "processing", "student": name, "index": idx, "total": total})
            try:
                pat = self._creds.retrieve(row["secret_ref"])
                local_path = row["local_path"]
                branch = row["branch"]

                self._git.ensure_remote(local_path, "canonical", canonical_path)
                self._git.fetch(local_path, "canonical")
                self._git.reset_hard(local_path, f"canonical/{canonical_branch}")
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
    # Operator sync methods
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

        return self.sync_student(student_id)

    def sync_student(self, student_id: str) -> SyncJob:
        """
        Canonical(master) → student repo.

        Target repo is hard-reset to canonical HEAD and then force-pushed.
        """
        canonical = self._canonical_context()
        student = self._student_context(student_id)

        job_id = self._create_job(
            repo_id=student["repo_id"],
            student_id=student_id,
            job_type=SyncJobType.sync_current,
            hash_before=student["hash_before"],
        )

        try:
            token = self._creds.retrieve(student["secret_ref"])

            self._git.fetch(canonical["local_path"], "origin")
            self._git.reset_hard(canonical["local_path"], f"origin/{canonical['branch']}")

            self._git.ensure_remote(student["local_path"], "canonical", canonical["local_path"])
            self._git.fetch(student["local_path"], "canonical")
            self._git.reset_hard(student["local_path"], f"canonical/{canonical['branch']}")
            self._git.push(
                student["local_path"],
                remote_name="student",
                branch=student["branch"],
                credential=token,
                auth_type=student["auth_type"],
                force=True,
            )

            hash_after = self._git.get_commit_hash(student["local_path"])
        except Exception as exc:
            self._fail_job(job_id, exc)
            self.update_repo_status(student["repo_id"], SyncStatus.error)
            raise SyncError(str(exc)) from exc

        job = self._succeed_job(job_id, hash_after, f"Canonical → student {hash_after[:8]}")
        self.update_repo_status(student["repo_id"], SyncStatus.clean, hash_after)
        self._audit.log(
            "sync_canonical_to_student",
            "sync_job",
            job_id,
            details={"repo_id": student["repo_id"], "student_id": student_id, "hash": hash_after},
        )
        return job

    def push_student_to_canonical(self, student_id: str) -> SyncJob:
        """
        Student repo → canonical(master) repo.

        Canonical target is hard-reset to student HEAD and then force-pushed to origin.
        """
        canonical = self._canonical_context()
        student = self._student_context(student_id)

        job_id = self._create_job(
            repo_id=student["repo_id"],
            student_id=student_id,
            job_type=SyncJobType.handoff_push,
            hash_before=student["hash_before"],
        )

        try:
            self._git.fetch(student["local_path"], "student")
            self._git.merge_ff_only(student["local_path"], f"student/{student['branch']}")

            self._git.ensure_remote(canonical["local_path"], "student_source", student["local_path"])
            self._git.fetch(canonical["local_path"], "student_source")
            self._git.reset_hard(canonical["local_path"], f"student_source/{student['branch']}")
            self._git.push(
                canonical["local_path"],
                remote_name="origin",
                branch=canonical["branch"],
                force=True,
            )

            hash_after = self._git.get_commit_hash(canonical["local_path"])
        except Exception as exc:
            self._fail_job(job_id, exc)
            self.update_repo_status(student["repo_id"], SyncStatus.error)
            self.update_repo_status(canonical["repo_id"], SyncStatus.error)
            raise SyncError(str(exc)) from exc

        job = self._succeed_job(job_id, hash_after, f"Student → canonical {hash_after[:8]}")
        self.update_repo_status(student["repo_id"], SyncStatus.clean, hash_after)
        self.update_repo_status(canonical["repo_id"], SyncStatus.clean, hash_after)
        self._audit.log(
            "sync_student_to_canonical",
            "sync_job",
            job_id,
            details={"repo_id": student["repo_id"], "student_id": student_id, "hash": hash_after},
        )
        return job

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
