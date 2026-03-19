"""Accounts router: account CRUD and validation."""
from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.account_service import AccountService

router = APIRouter(prefix="/accounts", tags=["accounts"])
_svc = AccountService()


class AccountCreate(BaseModel):
    student_id: str
    provider: str
    username: str
    auth_type: str
    is_current: bool = False


class AccountUpdate(BaseModel):
    provider: Optional[str] = None
    username: Optional[str] = None
    auth_type: Optional[str] = None
    status: Optional[str] = None
    is_current: Optional[bool] = None


def _account_dict(a) -> dict:
    return {
        "id": a.id,
        "student_id": a.student_id,
        "provider": a.provider,
        "username": a.username,
        "auth_type": a.auth_type,
        "status": a.status,
        "is_current": a.is_current,
        "last_validated_at": a.last_validated_at.isoformat() if a.last_validated_at else None,
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "updated_at": a.updated_at.isoformat() if a.updated_at else None,
    }


@router.get("")
def list_accounts(student_id: Optional[str] = None):
    if student_id is None:
        from app.db.base import SessionLocal
        from app.db.models import Account
        with SessionLocal() as session:
            accounts = session.query(Account).all()
            for a in accounts:
                session.expunge(a)
    else:
        accounts = _svc.list_for_student(student_id)
    return [_account_dict(a) for a in accounts]


@router.get("/{account_id}")
def get_account(account_id: str):
    account = _svc.get(account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return _account_dict(account)


@router.post("", status_code=201)
def create_account(body: AccountCreate):
    try:
        account = _svc.create(
            student_id=body.student_id,
            provider=body.provider,
            username=body.username,
            auth_type=body.auth_type,
            is_current=body.is_current,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _account_dict(account)


@router.put("/{account_id}")
def update_account(account_id: str, body: AccountUpdate):
    try:
        account = _svc.update(account_id, **body.model_dump(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(status_code=404 if "not found" in str(e).lower() else 400, detail=str(e))
    return _account_dict(account)


@router.delete("/{account_id}", status_code=204)
def deactivate_account(account_id: str):
    try:
        _svc.deactivate(account_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{account_id}/set-current")
def set_current_account(account_id: str):
    try:
        account = _svc.set_current(account_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return _account_dict(account)


@router.post("/{account_id}/mark-validated")
def mark_validated(account_id: str):
    try:
        account = _svc.mark_validated(account_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return _account_dict(account)
