from __future__ import annotations

import secrets
from collections.abc import Generator
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import hash_device_credential, password_hasher
from app.main import create_app
from app.models import Guest, Reservation, Room, RoomDevice, User
from tests.helpers import create_test_database


@pytest.fixture
def device_context() -> Generator[dict[str, object], None, None]:
    engine, session_factory = create_test_database()
    password = secrets.token_urlsafe(24)
    email = f"device-{secrets.token_hex(8)}@example.test"
    with Session(engine) as session:
        session.add_all(
            [
                User(
                    id=1,
                    name="Device Receptionist",
                    email=email,
                    password_hash=password_hasher.hash(password),
                    role="RECEPTION",
                    active=True,
                ),
                Guest(id=1, full_name="Guest Room 401", document="DEVICE-GUEST-1"),
                Guest(id=2, full_name="Private Guest 402", document="DEVICE-GUEST-2"),
                Room(id=1, number="401", category="Standard", capacity=2, status="OCCUPIED"),
                Room(id=2, number="402", category="Suite", capacity=2, status="OCCUPIED"),
                Reservation(
                    id=1,
                    guest_id=1,
                    room_id=1,
                    check_in_date=date.today(),
                    check_out_date=date.today() + timedelta(days=2),
                    guest_count=1,
                    status="CHECKED_IN",
                    actual_check_in_at=datetime.now(timezone.utc) - timedelta(hours=1),
                ),
                Reservation(
                    id=2,
                    guest_id=2,
                    room_id=2,
                    check_in_date=date.today(),
                    check_out_date=date.today() + timedelta(days=2),
                    guest_count=1,
                    status="CHECKED_IN",
                    actual_check_in_at=datetime.now(timezone.utc) - timedelta(hours=1),
                ),
            ]
        )
        session.commit()

    app = create_app(
        settings=Settings(
            database_url="postgresql+psycopg://unused:unused@localhost/unused",
            session_secret_key=secrets.token_urlsafe(48),
            session_cookie_secure=False,
        ),
        session_factory=session_factory,
    )
    with TestClient(app) as client:
        yield {
            "client": client,
            "session_factory": session_factory,
            "credentials": {"email": email, "password": password},
        }
    engine.dispose()


def login(context: dict[str, object]) -> TestClient:
    client = context["client"]
    assert isinstance(client, TestClient)
    assert client.post("/auth/login", json=context["credentials"]).status_code == 200
    return client


def create_pairing(context: dict[str, object], room_id: int = 1, code: str = "ROOM-401") -> dict:
    response = login(context).post(
        "/reception/room-devices",
        json={"room_id": room_id, "code": code},
    )
    assert response.status_code == 201
    return response.json()


def test_reception_creates_pairing_without_storing_plain_code(
    device_context: dict[str, object],
) -> None:
    payload = create_pairing(device_context)
    assert len(payload["pairing_code"]) == 12
    session_factory = device_context["session_factory"]
    with session_factory() as session:  # type: ignore[operator]
        device = session.scalar(select(RoomDevice).where(RoomDevice.code == "ROOM-401"))
        assert device is not None
        assert device.pairing_code_hash != payload["pairing_code"]
        assert password_hasher.verify(payload["pairing_code"], device.pairing_code_hash)
        assert device.active is False


def test_valid_pairing_authenticates_device_and_hides_credential(
    device_context: dict[str, object],
) -> None:
    pairing = create_pairing(device_context)
    client = device_context["client"]
    assert isinstance(client, TestClient)

    response = client.post(
        "/guest/pair",
        json={"code": "room-401", "pairing_code": pairing["pairing_code"]},
    )

    assert response.status_code == 200
    assert "hospitalitysync_device=" in response.headers["set-cookie"]
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=strict" in response.headers["set-cookie"]
    assert "Path=/guest" in response.headers["set-cookie"]
    credential = client.cookies.get("hospitalitysync_device")
    assert credential
    session_factory = device_context["session_factory"]
    with session_factory() as session:  # type: ignore[operator]
        device = session.scalar(select(RoomDevice).where(RoomDevice.code == "ROOM-401"))
        assert device is not None and device.active is True
        assert device.credential_hash == hash_device_credential(credential)
        assert credential != device.credential_hash
        assert device.pairing_code_hash is None


def test_invalid_and_expired_pairing_are_rejected(
    device_context: dict[str, object],
) -> None:
    pairing = create_pairing(device_context)
    client = device_context["client"]
    assert isinstance(client, TestClient)
    invalid = client.post(
        "/guest/pair",
        json={"code": "ROOM-401", "pairing_code": "00000000"},
    )
    assert invalid.status_code == 401

    session_factory = device_context["session_factory"]
    with session_factory() as session:  # type: ignore[operator]
        device = session.scalar(select(RoomDevice).where(RoomDevice.code == "ROOM-401"))
        assert device is not None
        device.pairing_expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        session.commit()
    expired = client.post(
        "/guest/pair",
        json={"code": "ROOM-401", "pairing_code": pairing["pairing_code"]},
    )
    assert expired.status_code == 401


def test_guest_dashboard_uses_device_room_and_isolates_other_guest(
    device_context: dict[str, object],
) -> None:
    pairing = create_pairing(device_context)
    client = device_context["client"]
    assert isinstance(client, TestClient)
    assert client.post(
        "/guest/pair",
        json={"code": "ROOM-401", "pairing_code": pairing["pairing_code"]},
    ).status_code == 200

    response = client.get("/guest")

    assert response.status_code == 200
    assert "Guest Room 401" in response.text
    assert "Quarto 401" in response.text
    assert "Private Guest 402" not in response.text


def test_guest_dashboard_requires_an_authenticated_device(
    device_context: dict[str, object],
) -> None:
    client = device_context["client"]
    assert isinstance(client, TestClient)
    assert client.get("/guest").status_code == 401


def test_revoke_immediately_blocks_device(device_context: dict[str, object]) -> None:
    pairing = create_pairing(device_context)
    client = device_context["client"]
    assert isinstance(client, TestClient)
    assert client.post(
        "/guest/pair",
        json={"code": "ROOM-401", "pairing_code": pairing["pairing_code"]},
    ).status_code == 200
    assert client.get("/guest").status_code == 200

    device_cookie = client.cookies.get("hospitalitysync_device")
    client.cookies.delete("hospitalitysync_device")
    assert client.post(f"/reception/room-devices/{pairing['id']}/revoke").status_code == 200
    client.cookies.set("hospitalitysync_device", device_cookie, path="/guest")
    assert client.get("/guest").status_code == 401


def test_only_one_active_device_per_room(device_context: dict[str, object]) -> None:
    first = create_pairing(device_context)
    client = device_context["client"]
    assert isinstance(client, TestClient)
    assert client.post(
        "/guest/pair",
        json={"code": "ROOM-401", "pairing_code": first["pairing_code"]},
    ).status_code == 200

    response = client.post(
        "/reception/room-devices",
        json={"room_id": 1, "code": "ROOM-401-BACKUP"},
    )
    assert response.status_code == 409


def test_device_management_requires_reception_authentication(
    device_context: dict[str, object],
) -> None:
    client = device_context["client"]
    assert isinstance(client, TestClient)
    assert client.get("/reception/room-devices").status_code == 401
    assert client.post(
        "/reception/room-devices",
        json={"room_id": 1, "code": "ROOM-401"},
    ).status_code == 401
