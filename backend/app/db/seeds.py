"""
Production seed data for StudentFlow.

Idempotent — safe to run multiple times.  Existing records (matched by
full_name / username+student_id) are skipped; the token is always
(re-)written to the OS keyring so it survives a keyring wipe.

The GitHub token is read exclusively from the environment variable GITHUB_TOKEN.
Never hard-code credentials here.  Set the variable before running:

    export GITHUB_TOKEN="<your-token>"
    python -m app.db.seeds
"""
from __future__ import annotations
import os
from app.db.base import SessionLocal
from app.db.enums import AccountStatus, AuthType, SecretKind, StudentStatus, SyncStatus
from app.security.vault import SecretVault

# ---------------------------------------------------------------------------
# Config — sourced from environment, never hard-coded
# ---------------------------------------------------------------------------
GITHUB_USERNAME = "maxfraieho"

# (full_name, repo_slug)  — remote_url = https://github.com/<repo_slug>
STUDENTS: list[tuple[str, str]] = [
    ("Emily Johnson",      "maxfraieho/comfort-hug-platform.git"),
    ("Michael Smith",      "maxfraieho/centered-greeting.git"),
    ("Olivia Brown",       "maxfraieho/welcome-page-creator.git"),
    ("James Davis",        "maxfraieho/equus-welcome-stage.git"),
    ("Sophia Wilson",      "maxfraieho/sweet-greeting-page.git"),
    ("William Miller",     "maxfraieho/centered-welcome-page.git"),
    ("Ava Moore",          "maxfraieho/welcome-duck-centered.git"),
    ("Benjamin Taylor",    "maxfraieho/center-stage-greeting.git"),
    ("Charlotte Anderson", "maxfraieho/centered-greeting-8ee5fb1f.git"),
    ("Daniel Thomas",      "maxfraieho/centered-welcome-pig.git"),
    ("Mia Jackson",        "maxfraieho/welcome-page.git"),
    ("Alexander White",    "maxfraieho/centered-welcome-page-0839a8f0.git"),
    ("Abigail Harris",     "maxfraieho/centered-greeting-54c71aca.git"),
    ("Joseph Martin",      "maxfraieho/centered-greeting-dc6ab9fe.git"),
    ("Emma Thompson",      "maxfraieho/welcome-page-5e8eea5d.git"),
    ("Matthew Garcia",     "maxfraieho/welcome-center.git"),
    ("Harper Martinez",    "maxfraieho/welcome-center-80896e62.git"),
    ("David Robinson",     "maxfraieho/welcome-page-951c20cc.git"),
    ("Grace Clark",        "maxfraieho/welcome-page-central.git"),
    ("Christopher Lewis",  "maxfraieho/welcome-page-pro.git"),
]


def _get_token() -> str:
    """Return the GitHub token from the environment. Raises clearly if not set."""
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError(
            "GITHUB_TOKEN environment variable is not set.\n"
            "Set it before running seeds:\n"
            "    export GITHUB_TOKEN='<your-token>'\n"
            "    python -m app.db.seeds"
        )
    return token


def _repo_name(repo_slug: str) -> str:
    """Extract repo name without owner prefix or .git suffix."""
    return repo_slug.split("/")[-1].removesuffix(".git")


def _local_path(idx: int, repo_slug: str) -> str:
    name = _repo_name(repo_slug)
    return f"/var/studentflow/repos/student-{idx:02d}-{name}"


def seed_demo_data() -> None:
    """Insert students, accounts, repos, credentials and write tokens to keyring."""
    import app.db.models  # noqa: F401 — ensures tables are registered
    from app.db.models import Account, ActivityLog, Credential, Repository, Student

    token = _get_token()
    vault = SecretVault()

    with SessionLocal() as session:
        existing_names = {s.full_name for s in session.query(Student).all()}

        for idx, (full_name, repo_slug) in enumerate(STUDENTS, start=1):
            # ── Student ──────────────────────────────────────────────
            if full_name in existing_names:
                student = session.query(Student).filter_by(full_name=full_name).first()
            else:
                student = Student(
                    full_name=full_name,
                    status=StudentStatus.active.value,
                    queue_position=idx,
                    student_number=idx,
                    notes=f"Student #{idx}",
                )
                session.add(student)
                session.flush()  # populate student.id

            # ── Account ──────────────────────────────────────────────
            existing_acc = session.query(Account).filter_by(
                student_id=student.id,
                username=GITHUB_USERNAME,
            ).first()

            if existing_acc:
                account = existing_acc
            else:
                account = Account(
                    student_id=student.id,
                    provider="github",
                    username=GITHUB_USERNAME,
                    auth_type=AuthType.pat.value,
                    status=AccountStatus.active.value,
                    is_current=True,
                )
                session.add(account)
                session.flush()  # populate account.id

            # ── Repository ───────────────────────────────────────────
            if not session.query(Repository).filter_by(account_id=account.id).first():
                session.add(Repository(
                    account_id=account.id,
                    repo_name=_repo_name(repo_slug),
                    remote_url=f"https://github.com/{repo_slug}",
                    local_path=_local_path(idx, repo_slug),
                    default_branch="main",
                    integration_branch="main",
                    sync_status=SyncStatus.uninitialized.value,
                    is_canonical=False,
                ))

            # ── Credential (DB row + keyring write) ──────────────────
            existing_cred = session.query(Credential).filter_by(account_id=account.id).first()
            if existing_cred:
                secret_ref = existing_cred.secret_ref
            else:
                secret_ref = SecretVault.make_key("github", GITHUB_USERNAME, account.id)
                session.add(Credential(
                    account_id=account.id,
                    secret_ref=secret_ref,
                    secret_kind=SecretKind.pat.value,
                    is_encrypted=True,
                ))

            # Always (re-)write the token so it survives a keyring wipe
            vault.set(secret_ref, token)

        # ── Seed marker audit log ─────────────────────────────────────
        from app.db.models import ActivityLog  # noqa: F811
        if session.query(ActivityLog).filter_by(action="seed_loaded").count() == 0:
            session.add(ActivityLog(
                actor="seed",
                entity_type="system",
                action="seed_loaded",
                details={"students": len(STUDENTS), "note": "Production seed data loaded"},
            ))

        session.commit()

    print(f"Seed complete — {len(STUDENTS)} students inserted/verified.")


if __name__ == "__main__":
    from app.bootstrap import create_app_dirs, init_db, init_logging
    create_app_dirs()
    init_logging()
    init_db()
    seed_demo_data()
