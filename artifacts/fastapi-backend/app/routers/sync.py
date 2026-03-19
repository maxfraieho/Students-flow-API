"""Sync router: trigger and monitor sync jobs."""
from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, HTTPException
from app.services.sync_service import SyncError, SyncService

router = APIRouter(prefix="/sync", tags=["sync"])
_svc = SyncService()


def _job_dict(j) -> dict:
    return {
        "id": j.id,
        "repo_id": j.repo_id,
        "student_id": j.student_id,
        "job_type": j.job_type,
        "status": j.status,
        "started_at": j.started_at.isoformat() if j.started_at else None,
        "finished_at": j.finished_at.isoformat() if j.finished_at else None,
        "summary": j.summary,
        "error_message": j.error_message,
        "commit_hash_before": j.commit_hash_before,
        "commit_hash_after": j.commit_hash_after,
        "created_at": j.created_at.isoformat() if j.created_at else None,
    }


@router.get("/jobs")
def list_jobs(student_id: Optional[str] = None, limit: int = 50):
    jobs = _svc.list_jobs(student_id=student_id, limit=limit)
    return [_job_dict(j) for j in jobs]


@router.post("/current")
def sync_current():
    try:
        job = _svc.sync_current_student()
    except SyncError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _job_dict(job)


@router.post("/student/{student_id}")
def sync_student(student_id: str):
    try:
        job = _svc.sync_student(student_id)
    except SyncError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _job_dict(job)
