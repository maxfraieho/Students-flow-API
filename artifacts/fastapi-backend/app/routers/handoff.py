"""Handoff router: trigger and query student handoff events."""
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from app.services.handoff_service import HandoffError, HandoffService, NoActiveStudentError, NoNextStudentError

router = APIRouter(prefix="/handoff", tags=["handoff"])
_svc = HandoffService()


def _event_dict(e) -> dict:
    return {
        "id": e.id,
        "from_student_id": e.from_student_id,
        "to_student_id": e.to_student_id,
        "repo_id": e.repo_id,
        "commit_hash": e.commit_hash,
        "checkpoint_tag": e.checkpoint_tag,
        "status": e.status,
        "notes": e.notes,
        "created_at": e.created_at.isoformat() if e.created_at else None,
        "completed_at": e.completed_at.isoformat() if e.completed_at else None,
    }


@router.get("/events")
def list_events(limit: int = 50):
    events = _svc.list_events(limit=limit)
    return [_event_dict(e) for e in events]


@router.get("/events/{event_id}")
def get_event(event_id: str):
    event = _svc.get_event(event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Handoff event not found")
    return _event_dict(event)


@router.post("")
def do_handoff():
    try:
        event = _svc.do_handoff()
    except NoActiveStudentError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except NoNextStudentError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except HandoffError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _event_dict(event)
