"""Sync router: trigger and monitor sync jobs, broadcast canonical."""
from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.services.sync_service import SyncError, SyncService

router = APIRouter(prefix="/sync", tags=["sync"])
_svc = SyncService()

_SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


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


@router.get("/broadcast")
def broadcast_canonical():
    """
    Stream a broadcast of the canonical repo to all active student repos.

    Returns a text/event-stream response.  Each SSE event carries a JSON
    payload describing progress::

        data: {"event": "processing", "student": "Alice", "index": 1, "total": 20}

        data: {"event": "done", "student": "Alice", "index": 1, "status": "success", "commit": "a1b2c3d4"}

        data: {"event": "broadcast_complete", "total": 20, "succeeded": 19, "failed": 1}

    The Cloudflare Worker must **not** buffer this response — it is already
    flushed as true SSE (``data: ...\\n\\n`` framing).
    """
    return StreamingResponse(
        _svc.broadcast_canonical_stream(),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )


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
