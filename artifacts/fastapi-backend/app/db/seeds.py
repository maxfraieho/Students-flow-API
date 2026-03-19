"""Demo seed data for StudentFlow. Idempotent — safe to run multiple times."""
import uuid
from datetime import datetime, timezone
from app.db.base import SessionLocal
from app.db.enums import AccountStatus, AuthType, SecretKind, StudentStatus, SyncStatus


DEMO_STUDENTS = [
    {"full_name": "Alice Kovalenko", "queue_position": 1, "status": StudentStatus.exhausted, "student_number": 1},
    {"full_name": "Bohdan Marchenko", "queue_position": 2, "status": StudentStatus.active, "student_number": 2},
    {"full_name": "Daria Lysenko", "queue_position": 3, "status": StudentStatus.paused, "student_number": 3},
    {"full_name": "Evhen Petrenko", "queue_position": 4, "status": StudentStatus.paused, "student_number": 4},
    {"full_name": "Fedir Bondarenko", "queue_position": 5, "status": StudentStatus.paused, "student_number": 5},
]

DEMO_ACCOUNTS = [
    {"provider": "github", "username": "alice-kovalenko", "auth_type": AuthType.pat, "secret_kind": SecretKind.pat},
    {"provider": "github", "username": "b-marchenko", "auth_type": AuthType.pat, "secret_kind": SecretKind.pat},
    {"provider": "gitlab", "username": "daria.lysenko", "auth_type": AuthType.ssh, "secret_kind": SecretKind.ssh_key},
    {"provider": "github", "username": "evhen-petrenko", "auth_type": AuthType.pat, "secret_kind": SecretKind.pat},
    {"provider": "bitbucket", "username": "fbondarenko", "auth_type": AuthType.app_password, "secret_kind": SecretKind.app_password},
]


def seed_demo_data() -> None:
    """Insert demo students, accounts, repos, credentials, and audit logs."""
    import app.db.models  # noqa: F401
    from app.db.models import Account, ActivityLog, Credential, Repository, Student

    with SessionLocal() as session:
        existing_names = {s.full_name for s in session.query(Student).all()}
        student_objects = []
        for s_data in DEMO_STUDENTS:
            if s_data["full_name"] in existing_names:
                student = session.query(Student).filter_by(full_name=s_data["full_name"]).first()
            else:
                student = Student(
                    full_name=s_data["full_name"],
                    status=s_data["status"].value,
                    queue_position=s_data["queue_position"],
                    student_number=s_data.get("student_number"),
                    notes=f"Demo student #{s_data['queue_position']}",
                )
                session.add(student)
            student_objects.append(student)
        session.flush()

        for i, (student, acc_data) in enumerate(zip(student_objects, DEMO_ACCOUNTS)):
            existing_acc = session.query(Account).filter_by(
                student_id=student.id, username=acc_data["username"]
            ).first()
            if existing_acc:
                account = existing_acc
            else:
                account = Account(
                    student_id=student.id,
                    provider=acc_data["provider"],
                    username=acc_data["username"],
                    auth_type=acc_data["auth_type"].value,
                    status=AccountStatus.active.value,
                )
                session.add(account)
                session.flush()

            if not session.query(Repository).filter_by(account_id=account.id).first():
                session.add(Repository(
                    account_id=account.id,
                    repo_name=f"student-project-{i + 1}",
                    remote_url=f"https://{acc_data['provider']}.com/{acc_data['username']}/student-project.git",
                    local_path=f"/tmp/studentflow-demo/repos/student-{i + 1}",
                    default_branch="main",
                    integration_branch="integration",
                    sync_status=SyncStatus.uninitialized.value,
                ))
                session.add(Credential(
                    account_id=account.id,
                    secret_ref=f"demo-token-ref-{i + 1}",
                    secret_kind=acc_data["secret_kind"].value,
                    is_encrypted=True,
                ))

        if session.query(ActivityLog).count() < 5:
            for action, entity_type, details in [
                ("student_created", "student", {"message": "Demo seed data loaded"}),
                ("sync_completed", "sync_job", {"message": "Initial demo sync"}),
            ]:
                session.add(ActivityLog(
                    actor="seed",
                    entity_type=entity_type,
                    action=action,
                    details=details,
                ))
        session.commit()
    print("Seed data inserted successfully.")


if __name__ == "__main__":
    from app.bootstrap import create_app_dirs, init_db, init_logging
    create_app_dirs()
    init_logging()
    init_db()
    seed_demo_data()
