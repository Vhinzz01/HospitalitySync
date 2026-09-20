from __future__ import annotations

import os
from dataclasses import dataclass


def _read_boolean(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default

    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise RuntimeError(f"{name} must be a boolean value.")


@dataclass(frozen=True, slots=True)
class Settings:
    database_url: str
    session_secret_key: str
    session_cookie_secure: bool = True
    session_max_age_seconds: int = 28_800
    device_cookie_max_age_seconds: int = 31_536_000
    enable_demo_access: bool = False

    def __post_init__(self) -> None:
        if not self.database_url.startswith(("postgresql://", "postgresql+psycopg://")):
            raise ValueError("DATABASE_URL must be a PostgreSQL SQLAlchemy URL.")
        if len(self.session_secret_key) < 32:
            raise ValueError("SESSION_SECRET_KEY must contain at least 32 characters.")
        if self.session_max_age_seconds <= 0:
            raise ValueError("SESSION_MAX_AGE_SECONDS must be greater than zero.")
        if self.device_cookie_max_age_seconds <= 0:
            raise ValueError("DEVICE_COOKIE_MAX_AGE_SECONDS must be greater than zero.")

    @classmethod
    def from_environment(cls) -> Settings:
        database_url = os.getenv("DATABASE_URL")
        session_secret_key = os.getenv("SESSION_SECRET_KEY")

        if not database_url:
            raise RuntimeError("DATABASE_URL is not set.")
        if not session_secret_key:
            raise RuntimeError("SESSION_SECRET_KEY is not set.")

        max_age_value = os.getenv("SESSION_MAX_AGE_SECONDS", "28800")
        device_max_age_value = os.getenv("DEVICE_COOKIE_MAX_AGE_SECONDS", "31536000")
        try:
            session_max_age_seconds = int(max_age_value)
            device_cookie_max_age_seconds = int(device_max_age_value)
        except ValueError as error:
            raise RuntimeError(
                "Session and device cookie max ages must be integers."
            ) from error

        return cls(
            database_url=database_url,
            session_secret_key=session_secret_key,
            session_cookie_secure=_read_boolean("SESSION_COOKIE_SECURE", True),
            session_max_age_seconds=session_max_age_seconds,
            device_cookie_max_age_seconds=device_cookie_max_age_seconds,
            enable_demo_access=_read_boolean("ENABLE_DEMO_ACCESS", False),
        )
