"""SQLAlchemy ORM models for the StudentFlow database schema."""
import uuid
from datetime import datetime
from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship
from app.db.base import Base
from app.db.enums import (
    AccountStatus,
    AuthType,
    HandoffStatus,
    PromptStatus,
    SecretKind,
    StudentStatus,
    SyncJobStatus,
    SyncJobType,
    SyncStatus,
)


class Student(Base):
    __tablename__ = "student"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    status = Column(String(20), nullable=False, default=StudentStatus.active.value)
    queue_position = Column(Integer, nullable=True)
    priority = Column(Integer, nullable=False, default=0)
    notes = Column(Text, nullable=True)
    student_number = Column(Integer, nullable=True, unique=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    accounts = relationship("Account", back_populates="student", cascade="all, delete-orphan")
    sync_jobs = relationship("SyncJob", back_populates="student")
    prompts = relationship("Prompt", back_populates="student")
    handoffs_from = relationship(
        "HandoffEvent",
        foreign_keys="HandoffEvent.from_student_id",
        back_populates="from_student",
    )
    handoffs_to = relationship(
        "HandoffEvent",
        foreign_keys="HandoffEvent.to_student_id",
        back_populates="to_student",
    )
    __table_args__ = (
        Index("idx_student_status", "status"),
        Index("idx_student_queue_position", "queue_position"),
        Index("idx_student_number", "student_number"),
    )


class Account(Base):
    __tablename__ = "account"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = Column(String(36), ForeignKey("student.id"), nullable=False)
    provider = Column(String(20), nullable=False)
    username = Column(String(255), nullable=False)
    auth_type = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, default=AccountStatus.unvalidated.value)
    last_validated_at = Column(DateTime, nullable=True)
    is_current = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    student = relationship("Student", back_populates="accounts")
    repositories = relationship("Repository", back_populates="account", cascade="all, delete-orphan")
    credential = relationship(
        "Credential",
        back_populates="account",
        cascade="all, delete-orphan",
        uselist=False,
    )
    __table_args__ = (
        Index("idx_account_student_id", "student_id"),
        Index("idx_account_is_current", "is_current"),
        Index("idx_account_status", "status"),
    )


class TemplateSource(Base):
    __tablename__ = "template_source"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    local_path = Column(String(255), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    checksum = Column(String(64), nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    repositories = relationship("Repository", back_populates="template_source")


class Repository(Base):
    __tablename__ = "repository"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    account_id = Column(String(36), ForeignKey("account.id"), nullable=False)
    repo_name = Column(String(255), nullable=False)
    remote_url = Column(String(255), nullable=False)
    local_path = Column(String(255), nullable=False)
    default_branch = Column(String(255), nullable=False, default="main")
    integration_branch = Column(String(255), nullable=False, default="main")
    sync_status = Column(String(20), nullable=False, default=SyncStatus.uninitialized.value)
    last_commit_hash = Column(String(40), nullable=True)
    template_source_id = Column(String(36), ForeignKey("template_source.id"), nullable=True)
    is_canonical = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    account = relationship("Account", back_populates="repositories")
    template_source = relationship("TemplateSource", back_populates="repositories")
    sync_jobs = relationship("SyncJob", back_populates="repository")
    handoff_events = relationship("HandoffEvent", back_populates="repository")
    prompts = relationship("Prompt", back_populates="repository")
    __table_args__ = (
        Index("idx_repository_account_id", "account_id"),
        Index("idx_repository_sync_status", "sync_status"),
        Index("idx_repository_is_canonical", "is_canonical"),
    )


class Credential(Base):
    __tablename__ = "credential"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    account_id = Column(String(36), ForeignKey("account.id"), nullable=False, unique=True)
    secret_ref = Column(String(255), nullable=False)
    secret_kind = Column(String(20), nullable=False)
    is_encrypted = Column(Boolean, nullable=False, default=True)
    last_validated_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    account = relationship("Account", back_populates="credential")


class SyncJob(Base):
    __tablename__ = "sync_job"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    repo_id = Column(String(36), ForeignKey("repository.id"), nullable=False)
    student_id = Column(String(36), ForeignKey("student.id"), nullable=False)
    job_type = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, default=SyncJobStatus.pending.value)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    summary = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    commit_hash_before = Column(String(40), nullable=True)
    commit_hash_after = Column(String(40), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    repository = relationship("Repository", back_populates="sync_jobs")
    student = relationship("Student", back_populates="sync_jobs")
    __table_args__ = (
        Index("idx_syncjob_repo_id", "repo_id"),
        Index("idx_syncjob_student_id", "student_id"),
        Index("idx_syncjob_status", "status"),
        Index("idx_syncjob_job_type", "job_type"),
    )


class HandoffEvent(Base):
    __tablename__ = "handoff_event"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    from_student_id = Column(String(36), ForeignKey("student.id"), nullable=True)
    to_student_id = Column(String(36), ForeignKey("student.id"), nullable=False)
    repo_id = Column(String(36), ForeignKey("repository.id"), nullable=False)
    commit_hash = Column(String(40), nullable=False)
    checkpoint_tag = Column(String(255), nullable=False)
    status = Column(String(20), nullable=False, default=HandoffStatus.pending.value)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    from_student = relationship("Student", foreign_keys=[from_student_id], back_populates="handoffs_from")
    to_student = relationship("Student", foreign_keys=[to_student_id], back_populates="handoffs_to")
    repository = relationship("Repository", back_populates="handoff_events")


class ActivityLog(Base):
    __tablename__ = "activity_log"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    actor = Column(String(100), nullable=False, default="operator")
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(String(36), nullable=True)
    action = Column(String(100), nullable=False)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    __table_args__ = (
        Index("idx_activitylog_entity_type", "entity_type"),
        Index("idx_activitylog_entity_id", "entity_id"),
        Index("idx_activitylog_created_at", "created_at"),
    )


class AppSetting(Base):
    __tablename__ = "app_setting"
    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class Prompt(Base):
    __tablename__ = "prompt"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = Column(String(36), ForeignKey("student.id"), nullable=False)
    repository_id = Column(String(36), ForeignKey("repository.id"), nullable=False)
    student_number = Column(Integer, nullable=False)
    seq_number = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False, default="")
    slug = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    file_path = Column(String(255), nullable=False)
    git_branch = Column(String(255), nullable=False)
    git_commit_hash = Column(String(40), nullable=True)
    status = Column(String(20), nullable=False, default=PromptStatus.draft.value)
    push_error = Column(Text, nullable=True)
    created_by = Column(String(100), nullable=False, default="operator")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    pushed_at = Column(DateTime, nullable=True)
    student = relationship("Student", back_populates="prompts")
    repository = relationship("Repository", back_populates="prompts")
    __table_args__ = (
        Index("idx_prompt_student_id", "student_id"),
        Index("idx_prompt_status", "status"),
        Index("idx_prompt_student_seq", "student_id", "seq_number"),
    )


__all__ = [
    "Student", "Account", "Repository", "Credential", "SyncJob",
    "HandoffEvent", "TemplateSource", "ActivityLog", "AppSetting", "Prompt",
]
