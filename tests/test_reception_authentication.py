from __future__ import annotations

import secrets
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import password_hasher
from app.main import create_app
from app.models import User
from tests.helpers import create_test_database


@pytest.fixture
def receptionist_credentials() -> dict[str, str]:
    return {
        "email": f"reception-{secrets.token_hex(8)}@example.test",
        "password": secrets.token_urlsafe(24),
    }


@pytest.fixture
def client(
    receptionist_credentials: dict[str, str],
) -> Generator[TestClient, None, None]:
    engine, session_factory = create_test_database()

    with Session(engine) as session:
        session.add(
            User(
                id=1,
                name="Reception Test User",
                email=receptionist_credentials["email"],
                password_hash=password_hasher.hash(
                    receptionist_credentials["password"]
                ),
                role="RECEPTION",
                active=True,
            )
        )
        session.commit()

    settings = Settings(
        database_url="postgresql+psycopg://unused:unused@localhost/unused",
        session_secret_key=secrets.token_urlsafe(48),
        session_cookie_secure=False,
    )
    app = create_app(settings=settings, session_factory=session_factory)

    with TestClient(app) as test_client:
        yield test_client

    engine.dispose()


def test_login_with_valid_credentials(
    client: TestClient,
    receptionist_credentials: dict[str, str],
) -> None:
    response = client.post("/auth/login", json=receptionist_credentials)

    assert response.status_code == 200
    assert response.json()["email"] == receptionist_credentials["email"]
    assert "password" not in response.json()
    assert "password_hash" not in response.json()
    assert "hospitalitysync_session" in client.cookies
    session_cookie = response.headers["set-cookie"].lower()
    assert "httponly" in session_cookie
    assert "samesite=lax" in session_cookie


def test_login_with_incorrect_password(
    client: TestClient,
    receptionist_credentials: dict[str, str],
) -> None:
    invalid_credentials = {
        **receptionist_credentials,
        "password": secrets.token_urlsafe(24),
    }

    response = client.post("/auth/login", json=invalid_credentials)

    assert response.status_code == 401
    assert response.json() == {"detail": "Email or password is invalid."}
    assert "hospitalitysync_session" not in client.cookies


def test_login_with_unknown_user(
    client: TestClient,
    receptionist_credentials: dict[str, str],
) -> None:
    unknown_credentials = {
        "email": f"unknown-{secrets.token_hex(8)}@example.test",
        "password": receptionist_credentials["password"],
    }

    response = client.post("/auth/login", json=unknown_credentials)

    assert response.status_code == 401
    assert response.json() == {"detail": "Email or password is invalid."}


def test_logout(
    client: TestClient,
    receptionist_credentials: dict[str, str],
) -> None:
    login_response = client.post("/auth/login", json=receptionist_credentials)
    assert login_response.status_code == 200

    logout_response = client.post("/auth/logout")

    assert logout_response.status_code == 204
    assert "hospitalitysync_session" not in client.cookies
    assert client.get("/reception").status_code == 401


def test_authenticated_access_to_reception(
    client: TestClient,
    receptionist_credentials: dict[str, str],
) -> None:
    client.post("/auth/login", json=receptionist_credentials)

    response = client.get("/reception")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert receptionist_credentials["email"] in response.text


def test_unauthenticated_access_to_reception(client: TestClient) -> None:
    response = client.get("/reception")

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required."}
