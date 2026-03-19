"""Students router: CRUD and queue management."""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.db.base import SessionLocal
from app.db.enums import StudentStatus
from app.db.models import Student

router = APIRouter(prefix="/students", tags=["students"])


class StudentCreate(BaseModel):
    full_name: str
    email: Optional[str] = None
    status: str = StudentStatus.paused.value
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


@router.get("")
def list_students(status: Optional[str] = None):
    with SessionLocal() as session:
        q = session.query(Student).order_by(Student.queue_position.asc(), Student.created_at.asc())
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
        allowed = {"full_name", "email", "status", "queue_position", "priority", "notes", "student_number"}
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
            raise HTTPException(status_code=409, detail=f"Student {existing_active.full_name} is already active")
        student = session.get(Student, student_id)
        if student is None:
            raise HTTPException(status_code=404, detail="Student not found")
        student.status = StudentStatus.active.value
        student.updated_at = datetime.utcnow()
        session.commit()
        session.refresh(student)
        session.expunge(student)
    return _student_dict(student)
