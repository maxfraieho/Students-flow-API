"""All enum types for StudentFlow database models."""
import enum


class StudentStatus(str, enum.Enum):
    active = "active"
    paused = "paused"
    exhausted = "exhausted"
    archived = "archived"
    error = "error"


class AccountProvider(str, enum.Enum):
    github = "github"
    gitlab = "gitlab"
    bitbucket = "bitbucket"
    gitea = "gitea"
    other = "other"


class AuthType(str, enum.Enum):
    ssh = "ssh"
    pat = "pat"
    app_password = "app_password"
    password = "password"


class AccountStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"
    error = "error"
    unvalidated = "unvalidated"


class SyncStatus(str, enum.Enum):
    clean = "clean"
    dirty = "dirty"
    diverged = "diverged"
    error = "error"
    uninitialized = "uninitialized"


class SyncJobType(str, enum.Enum):
    sync_current = "sync_current"
    sync_all = "sync_all"
    bootstrap = "bootstrap"
    handoff_push = "handoff_push"
    handoff_pull = "handoff_pull"


class SyncJobStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    success = "success"
    failed = "failed"
    skipped = "skipped"


class HandoffStatus(str, enum.Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"
    rolled_back = "rolled_back"


class EntityType(str, enum.Enum):
    student = "student"
    account = "account"
    repository = "repository"
    credential = "credential"
    sync_job = "sync_job"
    handoff = "handoff"
    template = "template"
    system = "system"


class SecretKind(str, enum.Enum):
    ssh_key = "ssh_key"
    pat = "pat"
    app_password = "app_password"
    password = "password"


class PromptStatus(str, enum.Enum):
    draft = "draft"
    written = "written"
    committed = "committed"
    pushed = "pushed"
    failed = "failed"
