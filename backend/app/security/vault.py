"""SecretVault: thin wrapper around the OS keyring via the keyring library."""
import os
import keyring
import keyring.errors
from typing import Optional

KEYRING_SERVICE = "studentflow"


class SecretVault:
    """Single interface for all OS keyring operations."""
    def __init__(self) -> None:
        # keyrings.cryptfile is interactive by default; prime it from env for headless services.
        backend = keyring.get_keyring()
        password = os.getenv("KEYRING_CRYPTFILE_PASSWORD")
        if password and getattr(type(backend), "keyring_key", None) is not None:
            backend.keyring_key = password

    def set(self, secret_ref: str, value: str) -> None:
        keyring.set_password(KEYRING_SERVICE, secret_ref, value)

    def get(self, secret_ref: str) -> Optional[str]:
        return keyring.get_password(KEYRING_SERVICE, secret_ref)

    def delete(self, secret_ref: str) -> None:
        keyring.delete_password(KEYRING_SERVICE, secret_ref)

    def exists(self, secret_ref: str) -> bool:
        return keyring.get_password(KEYRING_SERVICE, secret_ref) is not None

    @staticmethod
    def make_key(provider: str, username: str, account_id: str) -> str:
        return f"studentflow:{provider}:{username}:{account_id[:8]}"
