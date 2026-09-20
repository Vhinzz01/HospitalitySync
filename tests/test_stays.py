from __future__ import annotations

import base64
import json
import secrets
from collections.abc import Generator
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from itsdangerous import TimestampSigner
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import password_hasher
from app.main import create_app
from app.models import Guest, Reservation, Room, User
from tests.helpers import create_test_database


@pytest.fixture
def stay_context() -> Generator[dict[str, object], None, None]:
    engine, session_factory = create_test_database()
    password = secrets.token_urlsafe(24)
    email = f"stay-{secrets.token_hex(8)}@example.test"
    secret = secrets.token_urlsafe(48)
    with Session(engine) as session:
        session.add_all(
            [
                User(
                    id=1,
                    name="Stay Receptionist",
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
                Guest(
                    id=1,
                    full_name="Stay Guest",
                    document=f"STAY-{secrets.token_hex(6)}",
                    active=True,
                ),
                Room(
                    id=1,
                    number="301",
                    category="Standard",
                    capacity=2,
                    status="AVAILABLE",
                    active=True,
                ),
                Room(
                    id=2,
                    number="302",
                    category="Standard",
                    capacity=2,
                    status="MAINTENANCE",
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


def login(context: dict[str, object]) -> TestClient:
    client = context["client"]
    assert isinstance(client, TestClient)
    assert client.post("/auth/login", json=context["credentials"]).status_code == 200
    return client


def add_reservation(
    context: dict[str, object],
    *,
    room_id: int = 1,
    status: str = "CONFIRMED",
    check_in_date: date | None = None,
) -> int:
    session_factory = context["session_factory"]
    start = check_in_date or date.today()
    with session_factory() as session:  # type: ignore[operator]
        reservation = Reservation(
            guest_id=1,
            room_id=room_id,
            check_in_date=start,
            check_out_date=start + timedelta(days=2),
            guest_count=1,
            status=status,
            actual_check_in_at=(
                datetime.now(timezone.utc) - timedelta(hours=1)
                if status == "CHECKED_IN"
                else None
            ),
        )
        session.add(reservation)
        session.commit()
        return reservation.id


def test_check_in_creates_active_stay_and_occupies_room(
    stay_context: dict[str, object],
) -> None:
    client = login(stay_context)
    reservation_id = add_reservation(stay_context)

    response = client.post(f"/reception/reservations/{reservation_id}/check-in")

    assert response.status_code == 200
    assert response.json()["status"] == "CHECKED_IN"
    session_factory = stay_context["session_factory"]
    with session_factory() as session:  # type: ignore[operator]
        reservation = session.get(Reservation, reservation_id)
        room = session.get(Room, 1)
        assert reservation is not None and reservation.actual_check_in_at is not None
        assert room is not None and room.status == "OCCUPIED"


def test_check_in_rejects_early_arrival(stay_context: dict[str, object]) -> None:
    client = login(stay_context)
    reservation_id = add_reservation(
        stay_context, check_in_date=date.today() + timedelta(days=1)
    )

    response = client.post(f"/reception/reservations/{reservation_id}/check-in")

    assert response.status_code == 409
    assert "antes" in response.json()["detail"]


def test_check_in_requires_available_room(stay_context: dict[str, object]) -> None:
    client = login(stay_context)
    reservation_id = add_reservation(stay_context, room_id=2)

    response = client.post(f"/reception/reservations/{reservation_id}/check-in")

    assert response.status_code == 409
    assert "disponível" in response.json()["detail"]


def test_check_in_rejects_invalid_reservation_state(
    stay_context: dict[str, object],
) -> None:
    client = login(stay_context)
    reservation_id = add_reservation(stay_context, status="CANCELLED")

    response = client.post(f"/reception/reservations/{reservation_id}/check-in")

    assert response.status_code == 409


def test_check_out_finishes_stay_and_sends_room_to_cleaning(
    stay_context: dict[str, object],
) -> None:
    client = login(stay_context)
    reservation_id = add_reservation(stay_context)
    assert client.post(
        f"/reception/reservations/{reservation_id}/check-in"
    ).status_code == 200

    response = client.post(f"/reception/reservations/{reservation_id}/check-out")

    assert response.status_code == 200
    assert response.json()["status"] == "CHECKED_OUT"
    session_factory = stay_context["session_factory"]
    with session_factory() as session:  # type: ignore[operator]
        reservation = session.get(Reservation, reservation_id)
        room = session.get(Room, 1)
        assert reservation is not None and reservation.actual_check_out_at is not None
        assert room is not None and room.status == "CLEANING"


def test_check_out_requires_active_stay(stay_context: dict[str, object]) -> None:
    client = login(stay_context)
    reservation_id = add_reservation(stay_context)

    response = client.post(f"/reception/reservations/{reservation_id}/check-out")

    assert response.status_code == 409


def test_stay_routes_require_authentication(stay_context: dict[str, object]) -> None:
    client = stay_context["client"]
    assert isinstance(client, TestClient)
    assert client.get("/reception/check-in").status_code == 401
    assert client.post("/reception/reservations/1/check-in").status_code == 401


def test_stay_routes_reject_non_reception_role(
    stay_context: dict[str, object],
) -> None:
    client = stay_context["client"]
    secret = stay_context["secret"]
    assert isinstance(client, TestClient)
    assert isinstance(secret, str)
    encoded = base64.b64encode(json.dumps({"user_id": 2}).encode())
    client.cookies.set(
        "hospitalitysync_session",
        TimestampSigner(secret).sign(encoded).decode(),
    )

    assert client.get("/reception/check-out").status_code == 401
