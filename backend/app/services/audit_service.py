"""AuditService: structured audit trail and event recording."""
from __future__ import annotations
import json
import re
import sys
from datetime import datetime, timezone
from typing import Any
import structlog
from app.db.base import SessionLocal
from app.db.models import ActivityLog

log = structlog.get_logger(__name__)
_SECRET_PATTERNS = [
    r"ghp_[A-Za-z0-9]{36}",
    r"glpat-[A-Za-z0-9\-_]{20}",
    r"github_pat_[A-Za-z0-9_]{82}",
]
_VALID_ENTITY_TYPES = {
    "student", "account", "repository", "credential",
    "sync_job", "handoff_event", "app_setting", "prompt", "system",
}


class AuditService:
    def __init__(self, session_factory=None):
        self._session_factory = session_factory or SessionLocal

    def log(
        self,
        action: str,
        entity_type: str,
        entity_id: str | None = None,
        actor: str = "operator",
        details: dict[str, Any] | None = None,
    ) -> None:
        try:
            if entity_type not in _VALID_ENTITY_TYPES:
                raise ValueError(f"Unsupported entity_type: {entity_type}")
            sanitised_details = self._sanitise_details(details or {})
            timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
            try:
                with self._session_factory() as session:
                    record = ActivityLog(
                        actor=actor,
                        entity_type=entity_type,
                        entity_id=entity_id,
                        action=action,
                        details=json.dumps(sanitised_details),
                    )
                    session.add(record)
                    session.commit()
            except Exception as exc:
                self._stderr(f"AuditService.log DB insert failed: {exc}")
            log.info("audit", action=action, entity_type=entity_type,
                     entity_id=entity_id, actor=actor, details=sanitised_details, timestamp=timestamp)
        except Exception as exc:
            self._stderr(f"AuditService.log failed: {exc}")

    def get_logs(
        self,
        entity_type: str | None = None,
        entity_id: str | None = None,
        action: str | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> list[ActivityLog]:
        try:
            with self._session_factory() as session:
                query = session.query(ActivityLog)
                if entity_type is not None:
                    query = query.filter(ActivityLog.entity_type == entity_type)
                if entity_id is not None:
                    query = query.filter(ActivityLog.entity_id == entity_id)
                if action is not None:
                    query = query.filter(ActivityLog.action == action)
                rows = (query.order_by(ActivityLog.created_at.desc())
                        .offset(max(offset, 0)).limit(max(limit, 0)).all())
                for r in rows:
                    session.expunge(r)
                return rows
        except Exception as exc:
            self._stderr(f"AuditService.get_logs failed: {exc}")
            return []

    def _sanitise_details(self, details: dict[str, Any]) -> dict[str, Any]:
        payload = json.dumps(details)
        for pattern in _SECRET_PATTERNS:
            payload = re.sub(pattern, "[REDACTED]", payload)
        return json.loads(payload)

    @staticmethod
    def _stderr(message: str) -> None:
        print(message, file=sys.stderr)
