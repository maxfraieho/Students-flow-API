"""Students router: CRUD, queue management, and bulk import."""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator
from app.db.base import SessionLocal
from app.db.enums import AccountStatus, AuthType, SecretKind, StudentStatus, SyncStatus
from app.db.models import Account, Credential, Repository, Student
from app.security.vault import SecretVault

router = APIRouter(prefix="/students", tags=["students"])


# ──────────────────────────────────────────────────────────────────────────────
# Pydantic schemas
# ──────────────────────────────────────────────────────────────────────────────

class StudentCreate(BaseModel):
    full_name: str
    email: Optional[str] = None
    status: str = StudentStatus.active.value
    queue_position: Optional[int] = None
    priority: int = 0
    notes: Optional[str] = None
    student_number: Optional[int] = None


class StudentUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    status: Optional[str] = None
    queue_position: Optional[int] = None
    priority: Optional[int] = None
    notes: Optional[str] = None
    student_number: Optional[int] = None


class BulkImportItem(BaseModel):
    """One student row inside a bulk-import payload."""
    full_name: str
    github_username: str
    repo_url: str
    pat: str

    @field_validator("pat")
    @classmethod
    def pat_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("pat must not be empty")
        return v


class BulkImportPayload(BaseModel):
    students: list[BulkImportItem]


class BulkImportResult(BaseModel):
    full_name: str
    status: str                   # "created" | "skipped" | "failed"
    student_id: Optional[str] = None
    account_id: Optional[str] = None
    error: Optional[str] = None


class BulkImportResponse(BaseModel):
    created: int
    skipped: int
    failed: int
    results: list[BulkImportResult]


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _student_dict(s: Student) -> dict:
    return {
        "id": s.id,
        "full_name": s.full_name,
        "email": s.email,
        "status": s.status,
        "queue_position": s.queue_position,
        "priority": s.priority,
        "notes": s.notes,
        "student_number": s.student_number,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
    }


def _repo_name_from_url(repo_url: str) -> str:
    """Extract bare repo name from a GitHub URL."""
    return repo_url.rstrip("/").split("/")[-1].removesuffix(".git")


def _local_path(student_number: int, repo_url: str) -> str:
    name = _repo_name_from_url(repo_url)
    return f"/var/studentflow/repos/student-{student_number:02d}-{name}"


# ──────────────────────────────────────────────────────────────────────────────
# Standard CRUD endpoints
# ──────────────────────────────────────────────────────────────────────────────

@router.get("")
def list_students(status: Optional[str] = None):
    with SessionLocal() as session:
        q = session.query(Student).order_by(
            Student.queue_position.asc(), Student.created_at.asc()
        )
        if status:
            q = q.filter(Student.status == status)
        students = q.all()
        for s in students:
            session.expunge(s)
    return [_student_dict(s) for s in students]


@router.get("/active")
def get_active_student():
    with SessionLocal() as session:
        student = (
            session.query(Student)
            .filter(Student.status == StudentStatus.active.value)
            .order_by(Student.queue_position.asc(), Student.created_at.asc())
            .first()
        )
        if student is None:
            raise HTTPException(status_code=404, detail="No active student found")
        session.expunge(student)
    return _student_dict(student)


@router.get("/next")
def get_next_student():
    with SessionLocal() as session:
        student = (
            session.query(Student)
            .filter(Student.status.in_([StudentStatus.paused.value]))
            .order_by(Student.queue_position.asc(), Student.created_at.asc())
            .first()
        )
        if student is None:
            raise HTTPException(status_code=404, detail="No next student found")
        session.expunge(student)
    return _student_dict(student)


@router.get("/{student_id}")
def get_student(student_id: str):
    with SessionLocal() as session:
        student = session.get(Student, student_id)
        if student is None:
            raise HTTPException(status_code=404, detail="Student not found")
        session.expunge(student)
    return _student_dict(student)


@router.post("", status_code=201)
def create_student(body: StudentCreate):
    with SessionLocal() as session:
        student = Student(
            id=str(uuid.uuid4()),
            full_name=body.full_name,
            email=body.email,
            status=body.status,
            queue_position=body.queue_position,
            priority=body.priority,
            notes=body.notes,
            student_number=body.student_number,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(student)
        session.commit()
        session.refresh(student)
        session.expunge(student)
    return _student_dict(student)


@router.put("/{student_id}")
def update_student(student_id: str, body: StudentUpdate):
    with SessionLocal() as session:
        student = session.get(Student, student_id)
        if student is None:
            raise HTTPException(status_code=404, detail="Student not found")
        allowed = {
            "full_name", "email", "status", "queue_position",
            "priority", "notes", "student_number",
        }
        for field, value in body.model_dump(exclude_unset=True).items():
            if field in allowed and value is not None:
                setattr(student, field, value)
        student.updated_at = datetime.utcnow()
        session.commit()
        session.refresh(student)
        session.expunge(student)
    return _student_dict(student)


@router.delete("/{student_id}", status_code=204)
def archive_student(student_id: str):
    """
    Archive a student.

    Archived students are excluded from ``broadcast_canonical_stream``
    because that generator filters strictly on ``status == 'active'``.
    """
    with SessionLocal() as session:
        student = session.get(Student, student_id)
        if student is None:
            raise HTTPException(status_code=404, detail="Student not found")
        student.status = StudentStatus.archived.value
        student.updated_at = datetime.utcnow()
        session.commit()


@router.post("/{student_id}/activate")
def activate_student(student_id: str):
    with SessionLocal() as session:
        existing_active = (
            session.query(Student)
            .filter(Student.status == StudentStatus.active.value, Student.id != student_id)
            .first()
        )
        if existing_active:
            raise HTTPException(
                status_code=409,
                detail=f"Student {existing_active.full_name} is already active",
            )
        student = session.get(Student, student_id)
        if student is None:
            raise HTTPException(status_code=404, detail="Student not found")
        student.status = StudentStatus.active.value
        student.updated_at = datetime.utcnow()
        session.commit()
        session.refresh(student)
        session.expunge(student)
    return _student_dict(student)


# ──────────────────────────────────────────────────────────────────────────────
# Bulk import
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/bulk-import", status_code=207, response_model=BulkImportResponse)
def bulk_import_students(body: BulkImportPayload):
    """
    Create multiple students in one request.

    For each item the endpoint atomically creates:
    - ``Student``  (status=active)
    - ``Account``  (provider=github, auth_type=pat, is_current=True)
    - ``Repository``  (is_canonical=False, sync_status=uninitialized)
    - ``Credential``  (PAT stored in OS keyring via SecretVault — never logged)

    Students that already exist (matched by ``full_name``) are **skipped**,
    not duplicated.  Per-student errors do not abort the whole batch.

    Returns HTTP 207 Multi-Status so the frontend can inspect every result.
    """
    vault = SecretVault()
    results: list[BulkImportResult] = []
    created = skipped = failed = 0

    # Query current max queue_position and student_number to append safely
    with SessionLocal() as session:
        from sqlalchemy import func
        max_pos = session.query(func.max(Student.queue_position)).scalar() or 0
        max_num = session.query(func.max(Student.student_number)).scalar() or 0

    for idx, item in enumerate(body.students):
        student_number = max_num + idx + 1
        queue_position = max_pos + idx + 1

        try:
            with SessionLocal() as session:
                # ── Skip duplicates ───────────────────────────────────
                existing = (
                    session.query(Student)
                    .filter_by(full_name=item.full_name)
                    .first()
                )
                if existing is not None:
                    skipped += 1
                    results.append(BulkImportResult(
                        full_name=item.full_name,
                        status="skipped",
                        student_id=existing.id,
                    ))
                    continue

                now = datetime.utcnow()

                # ── Student ───────────────────────────────────────────
                student_id = str(uuid.uuid4())
                student = Student(
                    id=student_id,
                    full_name=item.full_name,
                    status=StudentStatus.active.value,
                    queue_position=queue_position,
                    student_number=student_number,
                    notes=f"Bulk import #{student_number}",
                    created_at=now,
                    updated_at=now,
                )
                session.add(student)
                session.flush()  # populate student.id

                # ── Account ───────────────────────────────────────────
                account_id = str(uuid.uuid4())
                account = Account(
                    id=account_id,
                    student_id=student_id,
                    provider="github",
                    username=item.github_username,
                    auth_type=AuthType.pat.value,
                    status=AccountStatus.active.value,
                    is_current=True,
                    created_at=now,
                    updated_at=now,
                )
                session.add(account)
                session.flush()  # populate account.id

                # ── Repository ────────────────────────────────────────
                repo_name = _repo_name_from_url(item.repo_url)
                session.add(Repository(
                    id=str(uuid.uuid4()),
                    account_id=account_id,
                    repo_name=repo_name,
                    remote_url=item.repo_url,
                    local_path=_local_path(student_number, item.repo_url),
                    default_branch="main",
                    integration_branch="main",
                    sync_status=SyncStatus.uninitialized.value,
                    is_canonical=False,
                    created_at=now,
                    updated_at=now,
                ))

                # ── Credential (PAT stored in OS keyring) ─────────────
                # secret_ref is derived from provider + username + account_id[:8]
                # the actual PAT value goes only to the keyring, never to the DB.
                secret_ref = SecretVault.make_key("github", item.github_username, account_id)
                vault.set(secret_ref, item.pat)   # keyring write — value never logged
                session.add(Credential(
                    id=str(uuid.uuid4()),
                    account_id=account_id,
                    secret_ref=secret_ref,
                    secret_kind=SecretKind.pat.value,
                    is_encrypted=True,
                    created_at=now,
                    updated_at=now,
                ))

                session.commit()

            created += 1
            results.append(BulkImportResult(
                full_name=item.full_name,
                status="created",
                student_id=student_id,
                account_id=account_id,
            ))

        except Exception as exc:
            failed += 1
            results.append(BulkImportResult(
                full_name=item.full_name,
                status="failed",
                error=str(exc)[:300],
            ))

    return BulkImportResponse(
        created=created,
        skipped=skipped,
        failed=failed,
        results=results,
    )
