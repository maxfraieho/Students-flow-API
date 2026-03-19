"""Settings router: read and update AppSetting key-value pairs."""
from __future__ import annotations
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.db.base import SessionLocal
from app.db.models import AppSetting

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingUpdate(BaseModel):
    value: str
    description: str | None = None


def _setting_dict(s) -> dict:
    return {
        "key": s.key,
        "value": s.value,
        "description": s.description,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
    }


@router.get("")
def list_settings():
    with SessionLocal() as session:
        settings = session.query(AppSetting).order_by(AppSetting.key.asc()).all()
        for s in settings:
            session.expunge(s)
    return [_setting_dict(s) for s in settings]


@router.get("/{key}")
def get_setting(key: str):
    with SessionLocal() as session:
        s = session.get(AppSetting, key)
        if s is None:
            raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")
        session.expunge(s)
    return _setting_dict(s)


@router.put("/{key}")
def update_setting(key: str, body: SettingUpdate):
    with SessionLocal() as session:
        s = session.get(AppSetting, key)
        if s is None:
            s = AppSetting(key=key, value=body.value,
                           description=body.description, updated_at=datetime.utcnow())
            session.add(s)
        else:
            s.value = body.value
            if body.description is not None:
                s.description = body.description
            s.updated_at = datetime.utcnow()
        session.commit()
        session.refresh(s)
        session.expunge(s)
    return _setting_dict(s)


@router.delete("/{key}", status_code=204)
def delete_setting(key: str):
    with SessionLocal() as session:
        s = session.get(AppSetting, key)
        if s is None:
            raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")
        session.delete(s)
        session.commit()
