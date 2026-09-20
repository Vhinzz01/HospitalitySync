from __future__ import annotations

import secrets
import hashlib

from pwdlib import PasswordHash
from pwdlib.exceptions import PwdlibError


class PasswordHasher:
    """Hashes and verifies passwords with pwdlib's recommended Argon2 settings."""

    def __init__(self) -> None:
        self._password_hash = PasswordHash.recommended()
        self._dummy_hash = self._password_hash.hash(secrets.token_urlsafe(32))

    def hash(self, password: str) -> str:
        return self._password_hash.hash(password)

    def verify(self, password: str, password_hash: str) -> bool:
        try:
            return self._password_hash.verify(password, password_hash)
        except (PwdlibError, ValueError):
            return False

    def verify_dummy(self, password: str) -> None:
        """Spend equivalent work when an email is absent to reduce timing leaks."""

        self._password_hash.verify(password, self._dummy_hash)


password_hasher = PasswordHasher()


def hash_device_credential(credential: str) -> str:
    """Create a deterministic lookup hash for a high-entropy device credential."""

    return hashlib.sha256(credential.encode("utf-8")).hexdigest()
