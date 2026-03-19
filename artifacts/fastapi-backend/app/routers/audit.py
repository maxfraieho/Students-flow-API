"""Audit router: query the activity log."""
from __future__ import annotations
from typing import Optional
from fastapi import APIRouter
from app.services.audit_service import AuditService

router = APIRouter(prefix="/audit", tags=["audit"])
_svc = AuditService()


def _log_dict(log) -> dict:
    return {
        "id": log.id,
        "actor": log.actor,
        "entity_type": log.entity_type,
        "entity_id": log.entity_id,
        "action": log.action,
        "details": log.details,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    }


@router.get("")
def get_logs(
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
):
    logs = _svc.get_logs(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        limit=limit,
        offset=offset,
    )
    return [_log_dict(log) for log in logs]
