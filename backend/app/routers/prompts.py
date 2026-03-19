"""Prompts router: create, push, and list prompt files."""
from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.prompt_service import PromptService

router = APIRouter(prefix="/prompts", tags=["prompts"])
_svc = PromptService()


class PromptCreate(BaseModel):
    title: str
    content: str
    created_by: str = "operator"


def _prompt_dict(p) -> dict:
    return {
        "id": p.id,
        "student_id": p.student_id,
        "repository_id": p.repository_id,
        "student_number": p.student_number,
        "seq_number": p.seq_number,
        "title": p.title,
        "slug": p.slug,
        "content": p.content,
        "file_path": p.file_path,
        "git_branch": p.git_branch,
        "git_commit_hash": p.git_commit_hash,
        "status": p.status,
        "push_error": p.push_error,
        "created_by": p.created_by,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "pushed_at": p.pushed_at.isoformat() if p.pushed_at else None,
    }


@router.get("")
def list_prompts(student_id: Optional[str] = None):
    prompts = _svc.list_prompts(student_id=student_id)
    return [_prompt_dict(p) for p in prompts]


@router.get("/{prompt_id}")
def get_prompt(prompt_id: str):
    p = _svc.get(prompt_id)
    if p is None:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return _prompt_dict(p)


@router.post("", status_code=201)
def create_prompt(body: PromptCreate):
    try:
        p = _svc.create_and_push_prompt(
            title=body.title,
            content=body.content,
            created_by=body.created_by,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _prompt_dict(p)


@router.post("/{prompt_id}/retry")
def retry_prompt(prompt_id: str):
    try:
        p = _svc.retry_push(prompt_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _prompt_dict(p)
