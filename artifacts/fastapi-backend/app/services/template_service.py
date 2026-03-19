"""TemplateService: template source registration and validation."""
from __future__ import annotations
import hashlib
from datetime import datetime
from pathlib import Path
from app.db.base import SessionLocal
from app.db.models import TemplateSource


class TemplateService:
    def __init__(self, session_factory=None):
        self._session_factory = session_factory or SessionLocal

    def register(self, name: str, local_path: str, description: str = "") -> TemplateSource:
        path = Path(local_path)
        if not path.exists() or not path.is_dir():
            raise ValueError(f"Template path does not exist or is not a directory: {local_path}")
        checksum = self._checksum(path)
        with self._session_factory() as session:
            template = TemplateSource(
                name=name,
                local_path=str(path.resolve()),
                is_active=True,
                checksum=checksum,
                description=description,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            session.add(template)
            session.commit()
            session.refresh(template)
            session.expunge(template)
            return template

    def validate_template(self, template: TemplateSource) -> bool:
        path = Path(template.local_path)
        if not path.exists() or not path.is_dir():
            return False
        current_checksum = self._checksum(path)
        return current_checksum == template.checksum

    def list_active(self) -> list[TemplateSource]:
        with self._session_factory() as session:
            templates = session.query(TemplateSource).filter_by(is_active=True).all()
            for t in templates:
                session.expunge(t)
            return templates

    def get(self, template_id: str) -> TemplateSource | None:
        with self._session_factory() as session:
            t = session.get(TemplateSource, template_id)
            if t:
                session.expunge(t)
            return t

    def deactivate(self, template_id: str) -> TemplateSource:
        with self._session_factory() as session:
            t = session.get(TemplateSource, template_id)
            if t is None:
                raise ValueError(f"TemplateSource {template_id} not found")
            t.is_active = False
            t.updated_at = datetime.utcnow()
            session.commit()
            session.refresh(t)
            session.expunge(t)
            return t

    @staticmethod
    def _checksum(path: Path) -> str:
        h = hashlib.sha256()
        for f in sorted(path.rglob("*")):
            if f.is_file():
                h.update(f.read_bytes())
        return h.hexdigest()[:64]
