"""Repositories router: repository registration and status."""
from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.repository_service import RepositoryService

router = APIRouter(prefix="/repositories", tags=["repositories"])
_svc = RepositoryService()


class RepoRegister(BaseModel):
    account_id: str
    repo_name: str
    remote_url: str
    local_path: str
    default_branch: str = "main"
    is_canonical: bool = False


def _repo_dict(r) -> dict:
    return {
        "id": r.id,
        "account_id": r.account_id,
        "repo_name": r.repo_name,
        "remote_url": r.remote_url,
        "local_path": r.local_path,
        "default_branch": r.default_branch,
        "integration_branch": r.integration_branch,
        "sync_status": r.sync_status,
        "last_commit_hash": r.last_commit_hash,
        "is_canonical": r.is_canonical,
        "template_source_id": r.template_source_id,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
    }


@router.get("")
def list_repositories(student_id: Optional[str] = None):
    if student_id:
        repos = _svc.list_repos_for_student(student_id)
    else:
        repos = _svc.list_all()
    return [_repo_dict(r) for r in repos]


@router.get("/canonical")
def get_canonical():
    repo = _svc.get_canonical_repo()
    if repo is None:
        raise HTTPException(status_code=404, detail="No canonical repository configured")
    return _repo_dict(repo)


@router.get("/{repo_id}")
def get_repository(repo_id: str):
    repo = _svc.get(repo_id)
    if repo is None:
        raise HTTPException(status_code=404, detail="Repository not found")
    return _repo_dict(repo)


@router.post("", status_code=201)
def register_repository(body: RepoRegister):
    try:
        repo = _svc.register_existing(
            account_id=body.account_id,
            repo_name=body.repo_name,
            remote_url=body.remote_url,
            local_path=body.local_path,
            default_branch=body.default_branch,
            is_canonical=body.is_canonical,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _repo_dict(repo)


@router.post("/{repo_id}/validate-remote")
def validate_remote(repo_id: str):
    ok = _svc.validate_remote(repo_id)
    return {"repo_id": repo_id, "remote_reachable": ok}


@router.get("/{repo_id}/status")
def get_status(repo_id: str):
    try:
        status = _svc.get_repo_status(repo_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"repo_id": repo_id, "sync_status": status.value}
