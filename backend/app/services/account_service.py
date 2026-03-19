"""AccountService: student account lifecycle management."""
from __future__ import annotations
from datetime import datetime
from typing import Optional
import structlog
from app.db.base import SessionLocal
from app.db.models import Account, Student
from app.db.enums import AccountStatus, AccountProvider, AuthType

logger = structlog.get_logger(__name__)


class AccountService:
    def __init__(self, session_factory=None):
        self._session_factory = session_factory or SessionLocal

    def create(
        self,
        student_id: str,
        provider: str,
        username: str,
        auth_type: str,
        is_current: bool = False,
    ) -> Account:
        with self._session_factory() as session:
            student = session.get(Student, student_id)
            if student is None:
                raise ValueError(f"Student {student_id} not found")
            account = Account(
                student_id=student_id,
                provider=provider,
                username=username,
                auth_type=auth_type,
                status=AccountStatus.unvalidated.value,
                is_current=is_current,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            session.add(account)
            if is_current:
                session.query(Account).filter(
                    Account.student_id == student_id,
                    Account.id != account.id,
                ).update({"is_current": False})
            session.commit()
            session.refresh(account)
            session.expunge(account)
            logger.info("account_created", student_id=student_id, provider=provider, username=username)
            return account

    def get(self, account_id: str) -> Optional[Account]:
        with self._session_factory() as session:
            account = session.get(Account, account_id)
            if account:
                session.expunge(account)
            return account

    def list_for_student(self, student_id: str) -> list[Account]:
        with self._session_factory() as session:
            accounts = session.query(Account).filter_by(student_id=student_id).all()
            for a in accounts:
                session.expunge(a)
            return accounts

    def update(self, account_id: str, **fields) -> Account:
        with self._session_factory() as session:
            account = session.get(Account, account_id)
            if account is None:
                raise ValueError(f"Account {account_id} not found")
            allowed = {"provider", "username", "auth_type", "status", "is_current", "last_validated_at"}
            for key, value in fields.items():
                if key in allowed:
                    setattr(account, key, value)
            if fields.get("is_current"):
                session.query(Account).filter(
                    Account.student_id == account.student_id,
                    Account.id != account_id,
                ).update({"is_current": False})
            account.updated_at = datetime.utcnow()
            session.commit()
            session.refresh(account)
            session.expunge(account)
            return account

    def deactivate(self, account_id: str) -> Account:
        return self.update(account_id, status=AccountStatus.inactive.value)

    def set_current(self, account_id: str) -> Account:
        with self._session_factory() as session:
            account = session.get(Account, account_id)
            if account is None:
                raise ValueError(f"Account {account_id} not found")
            session.query(Account).filter_by(student_id=account.student_id).update({"is_current": False})
            account.is_current = True
            account.updated_at = datetime.utcnow()
            session.commit()
            session.refresh(account)
            session.expunge(account)
            return account

    def mark_validated(self, account_id: str) -> Account:
        return self.update(
            account_id,
            status=AccountStatus.active.value,
            last_validated_at=datetime.utcnow(),
        )
