"""CredentialService: manages keyring-based credentials and Credential DB records."""
from __future__ import annotations
from datetime import datetime
from typing import Optional
import structlog
from app.db.base import SessionLocal
from app.db.models import Credential, Account
from app.db.enums import SecretKind
from app.security.vault import SecretVault

logger = structlog.get_logger(__name__)


class CredentialService:
    def __init__(self, vault: Optional[SecretVault] = None, session_factory=None):
        self._vault = vault or SecretVault()
        self._session_factory = session_factory or SessionLocal

    def store(self, account_id: str, secret_kind: SecretKind, value: str) -> Credential:
        with self._session_factory() as session:
            account = session.get(Account, account_id)
            if account is None:
                raise ValueError(f"Account {account_id} not found")
            existing = session.query(Credential).filter_by(account_id=account_id).first()
            if existing is not None:
                raise ValueError(f"Credential already exists for account {account_id}. Use rotate() to update.")
            secret_ref = SecretVault.make_key(
                provider=account.provider,
                username=account.username,
                account_id=account_id,
            )
            self._vault.set(secret_ref, value)
            credential = Credential(
                account_id=account_id,
                secret_ref=secret_ref,
                secret_kind=secret_kind.value if isinstance(secret_kind, SecretKind) else secret_kind,
                is_encrypted=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            session.add(credential)
            session.commit()
            session.refresh(credential)
            logger.info("credential_stored", account_id=account_id, secret_kind=str(secret_kind))
            return credential

    def retrieve(self, secret_ref: str) -> str:
        value = self._vault.get(secret_ref)
        if value is None:
            logger.warning("credential_not_found", secret_ref=secret_ref)
            raise KeyError(f"No credential found for key: {secret_ref}")
        return value

    def rotate(self, credential_id: str, new_value: str) -> None:
        with self._session_factory() as session:
            credential = session.get(Credential, credential_id)
            if credential is None:
                raise ValueError(f"Credential {credential_id} not found")
            self._vault.set(credential.secret_ref, new_value)
            credential.last_validated_at = datetime.utcnow()
            credential.updated_at = datetime.utcnow()
            session.commit()
            logger.info("credential_rotated", credential_id=credential_id, account_id=credential.account_id)

    def delete(self, secret_ref: str) -> None:
        with self._session_factory() as session:
            credential = session.query(Credential).filter_by(secret_ref=secret_ref).first()
            try:
                self._vault.delete(secret_ref)
            except Exception as e:
                logger.warning("credential_delete_keyring_error", secret_ref=secret_ref, error=str(e))
            if credential is not None:
                session.delete(credential)
                session.commit()
                logger.info("credential_deleted", account_id=credential.account_id)

    def validate_exists(self, secret_ref: str) -> bool:
        return self._vault.exists(secret_ref)

    def get_by_account(self, account_id: str) -> Optional[Credential]:
        with self._session_factory() as session:
            cred = session.query(Credential).filter_by(account_id=account_id).first()
            if cred:
                session.expunge(cred)
            return cred
