"""Credentials router: store, rotate, and delete credentials."""
from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.db.enums import SecretKind
from app.services.credential_service import CredentialService

router = APIRouter(prefix="/credentials", tags=["credentials"])
_svc = CredentialService()


class CredentialStore(BaseModel):
    account_id: str
    secret_kind: str
    value: str


class CredentialRotate(BaseModel):
    value: str


def _cred_dict(c) -> dict:
    return {
        "id": c.id,
        "account_id": c.account_id,
        "secret_ref": c.secret_ref,
        "secret_kind": c.secret_kind,
        "is_encrypted": c.is_encrypted,
        "last_validated_at": c.last_validated_at.isoformat() if c.last_validated_at else None,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    }


@router.get("")
def list_credentials(account_id: Optional[str] = None):
    from app.db.base import SessionLocal
    from app.db.models import Credential
    with SessionLocal() as session:
        q = session.query(Credential)
        if account_id:
            q = q.filter_by(account_id=account_id)
        creds = q.all()
        for c in creds:
            session.expunge(c)
    return [_cred_dict(c) for c in creds]


@router.post("", status_code=201)
def store_credential(body: CredentialStore):
    try:
        kind = SecretKind(body.secret_kind)
        cred = _svc.store(body.account_id, kind, body.value)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _cred_dict(cred)


@router.put("/{credential_id}/rotate")
def rotate_credential(credential_id: str, body: CredentialRotate):
    try:
        _svc.rotate(credential_id, body.value)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"message": "Credential rotated successfully"}


@router.delete("/{credential_id}", status_code=204)
def delete_credential(credential_id: str):
    from app.db.base import SessionLocal
    from app.db.models import Credential
    with SessionLocal() as session:
        cred = session.get(Credential, credential_id)
        if cred is None:
            raise HTTPException(status_code=404, detail="Credential not found")
        secret_ref = cred.secret_ref
    try:
        _svc.delete(secret_ref)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{credential_id}/exists")
def check_exists(credential_id: str):
    from app.db.base import SessionLocal
    from app.db.models import Credential
    with SessionLocal() as session:
        cred = session.get(Credential, credential_id)
        if cred is None:
            raise HTTPException(status_code=404, detail="Credential not found")
        secret_ref = cred.secret_ref
    exists = _svc.validate_exists(secret_ref)
    return {"credential_id": credential_id, "exists_in_keyring": exists}
