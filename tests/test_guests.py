from __future__ import annotations

import base64
import json
import secrets
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from itsdangerous import TimestampSigner
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import password_hasher
from app.main import create_app
from app.models import Guest, User
from tests.helpers import create_test_database


@pytest.fixture
def guest_context() -> Generator[dict[str, object], None, None]:
    engine, session_factory = create_test_database()
    password = secrets.token_urlsafe(24)
    email = f"guest-management-{secrets.token_hex(8)}@example.test"
    secret = secrets.token_urlsafe(48)
    with Session(engine) as session:
        session.add_all(
            [
                User(
                    id=1,
                    name="Guest Receptionist",
                    email=email,
                    password_hash=password_hasher.hash(password),
                    role="RECEPTION",
                    active=True,
                ),
                User(
                    id=2,
                    name="Kitchen User",
                    email=f"kitchen-{secrets.token_hex(8)}@example.test",
                    password_hash=password_hasher.hash(secrets.token_urlsafe(24)),
                    role="KITCHEN",
                    active=True,
                ),
            ]
        )
        session.commit()
    app = create_app(
        settings=Settings(
            database_url="postgresql+psycopg://unused:unused@localhost/unused",
            session_secret_key=secret,
            session_cookie_secure=False,
        ),
        session_factory=session_factory,
    )
    with TestClient(app) as client:
        yield {
            "client": client,
            "session_factory": session_factory,
            "credentials": {"email": email, "password": password},
            "secret": secret,
        }
    engine.dispose()


def authenticated_client(context: dict[str, object]) -> TestClient:
    client = context["client"]
    assert isinstance(client, TestClient)
    response = client.post("/auth/login", json=context["credentials"])
    assert response.status_code == 200
    return client


def guest_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "full_name": "Helena Duarte",
        "document": f"DOC-{secrets.token_hex(5)}",
        "email": "helena@example.test",
        "phone": "+55 11 99999-0000",
    }
    payload.update(overrides)
    return payload


def test_create_and_list_guest(guest_context: dict[str, object]) -> None:
    client = authenticated_client(guest_context)
    payload = guest_payload(document="guest-doc-one")

    created = client.post("/reception/guests", json=payload)
    page = client.get("/reception/guests?state=active&search=Helena")

    assert created.status_code == 201
    assert created.json()["document"] == "GUEST-DOC-ONE"
    assert page.status_code == 200
    assert "Helena Duarte" in page.text
    assert "GUEST-DOC-ONE" in page.text


def test_update_guest(guest_context: dict[str, object]) -> None:
    client = authenticated_client(guest_context)
    guest_id = client.post(
        "/reception/guests", json=guest_payload(document="update-doc")
    ).json()["id"]

    response = client.put(
        f"/reception/guests/{guest_id}",
        json=guest_payload(
            full_name="Helena Duarte Silva",
            document="updated-doc",
            phone=None,
        ),
    )

    assert response.status_code == 200
    assert response.json()["full_name"] == "Helena Duarte Silva"
    assert response.json()["document"] == "UPDATED-DOC"
    assert response.json()["phone"] is None


def test_deactivate_guest_without_deleting(guest_context: dict[str, object]) -> None:
    client = authenticated_client(guest_context)
    guest_id = client.post(
        "/reception/guests", json=guest_payload(document="deactivate-doc")
    ).json()["id"]

    response = client.post(f"/reception/guests/{guest_id}/deactivate")

    assert response.status_code == 200
    assert response.json()["active"] is False
    session_factory = guest_context["session_factory"]
    with session_factory() as session:  # type: ignore[operator]
        assert session.get(Guest, guest_id) is not None


def test_duplicate_document_is_rejected(guest_context: dict[str, object]) -> None:
    client = authenticated_client(guest_context)
    assert client.post(
        "/reception/guests", json=guest_payload(document="same-doc")
    ).status_code == 201

    response = client.post(
        "/reception/guests", json=guest_payload(document="SAME-DOC")
    )

    assert response.status_code == 409


def test_invalid_email_is_rejected(guest_context: dict[str, object]) -> None:
    client = authenticated_client(guest_context)

    response = client.post(
        "/reception/guests",
        json=guest_payload(email="invalid-email"),
    )

    assert response.status_code == 400


def test_unknown_guest_returns_not_found(guest_context: dict[str, object]) -> None:
    client = authenticated_client(guest_context)

    response = client.put("/reception/guests/999999", json=guest_payload())

    assert response.status_code == 404


def test_guest_routes_require_authentication(guest_context: dict[str, object]) -> None:
    client = guest_context["client"]
    assert isinstance(client, TestClient)

    assert client.get("/reception/guests").status_code == 401
    assert client.post("/reception/guests", json=guest_payload()).status_code == 401


def test_guest_routes_reject_non_reception_role(
    guest_context: dict[str, object],
) -> None:
    client = guest_context["client"]
    secret = guest_context["secret"]
    assert isinstance(client, TestClient)
    assert isinstance(secret, str)
    encoded = base64.b64encode(json.dumps({"user_id": 2}).encode())
    cookie = TimestampSigner(secret).sign(encoded).decode()
    client.cookies.set("hospitalitysync_session", cookie)

    response = client.get("/reception/guests")

    assert response.status_code == 401
