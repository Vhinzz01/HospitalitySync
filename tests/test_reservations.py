from __future__ import annotations

import base64
import json
import secrets
from collections.abc import Generator
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from itsdangerous import TimestampSigner
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import password_hasher
from app.main import create_app
from app.models import Guest, Reservation, Room, User
from app.repositories import ReservationRepository
from app.schemas import ReservationWriteRequest
from app.services import ReservationConflictError, ReservationService
from tests.helpers import create_test_database


@pytest.fixture
def reservation_context() -> Generator[dict[str, object], None, None]:
    engine, session_factory = create_test_database()
    receptionist_password = secrets.token_urlsafe(24)
    kitchen_password = secrets.token_urlsafe(24)
    receptionist_email = f"reservations-{secrets.token_hex(8)}@example.test"
    kitchen_email = f"kitchen-{secrets.token_hex(8)}@example.test"
    session_secret = secrets.token_urlsafe(48)

    with Session(engine) as session:
        session.add_all(
            [
                User(
                    id=1,
                    name="Reservation Receptionist",
                    email=receptionist_email,
                    password_hash=password_hasher.hash(receptionist_password),
                    role="RECEPTION",
                    active=True,
                ),
                User(
                    id=2,
                    name="Kitchen User",
                    email=kitchen_email,
                    password_hash=password_hasher.hash(kitchen_password),
                    role="KITCHEN",
                    active=True,
                ),
                Guest(
                    id=1,
                    full_name="Alice Moreira",
                    document=f"DOC-{secrets.token_hex(6)}",
                    active=True,
                ),
                Guest(
                    id=2,
                    full_name="Bruno Alves",
                    document=f"DOC-{secrets.token_hex(6)}",
                    active=True,
                ),
                Room(
                    id=1,
                    number="201",
                    category="Standard",
                    capacity=2,
                    status="AVAILABLE",
                    active=True,
                ),
                Room(
                    id=2,
                    number="202",
                    category="Suíte",
                    capacity=4,
                    status="AVAILABLE",
                    active=True,
                ),
            ]
        )
        session.commit()

    settings = Settings(
        database_url="postgresql+psycopg://unused:unused@localhost/unused",
        session_secret_key=session_secret,
        session_cookie_secure=False,
    )
    app = create_app(settings=settings, session_factory=session_factory)

    with TestClient(app) as client:
        yield {
            "client": client,
            "engine": engine,
            "session_factory": session_factory,
            "session_secret": session_secret,
            "receptionist": {
                "email": receptionist_email,
                "password": receptionist_password,
            },
            "kitchen": {"email": kitchen_email, "password": kitchen_password},
        }

    engine.dispose()


def login_receptionist(context: dict[str, object]) -> TestClient:
    client = context["client"]
    assert isinstance(client, TestClient)
    credentials = context["receptionist"]
    assert isinstance(credentials, dict)
    response = client.post("/auth/login", json=credentials)
    assert response.status_code == 200
    return client


def valid_payload(**overrides: object) -> dict[str, object]:
    start = date.today() + timedelta(days=10)
    payload: dict[str, object] = {
        "guest_id": 1,
        "room_id": 1,
        "check_in_date": start.isoformat(),
        "check_out_date": (start + timedelta(days=3)).isoformat(),
        "guest_count": 1,
    }
    payload.update(overrides)
    return payload


def test_create_valid_reservation(reservation_context: dict[str, object]) -> None:
    client = login_receptionist(reservation_context)

    response = client.post("/reception/reservations", json=valid_payload())

    assert response.status_code == 201
    assert response.json()["status"] == "CONFIRMED"
    assert response.json()["guest_name"] == "Alice Moreira"
    assert response.json()["room_number"] == "201"
    session_factory = reservation_context["session_factory"]
    with session_factory() as session:  # type: ignore[operator]
        stored = session.get(Reservation, response.json()["id"])
        assert stored is not None
        assert stored.status == "CONFIRMED"


def test_list_reservations_displays_database_records(
    reservation_context: dict[str, object],
) -> None:
    client = login_receptionist(reservation_context)
    created = client.post("/reception/reservations", json=valid_payload())
    assert created.status_code == 201

    response = client.get("/reception/reservations?status=CONFIRMED")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Alice Moreira" in response.text
    assert "201" in response.text
    assert f'data-reservation-id="{created.json()["id"]}"' in response.text


def test_prevent_overlapping_reservation(
    reservation_context: dict[str, object],
) -> None:
    client = login_receptionist(reservation_context)
    first_response = client.post("/reception/reservations", json=valid_payload())
    assert first_response.status_code == 201
    start = date.today() + timedelta(days=11)

    response = client.post(
        "/reception/reservations",
        json=valid_payload(
            check_in_date=start.isoformat(),
            check_out_date=(start + timedelta(days=4)).isoformat(),
        ),
    )

    assert response.status_code == 409
    assert "reserva ativa" in response.json()["detail"]


def test_edit_reservation(reservation_context: dict[str, object]) -> None:
    client = login_receptionist(reservation_context)
    created = client.post("/reception/reservations", json=valid_payload()).json()
    new_start = date.today() + timedelta(days=20)

    response = client.put(
        f"/reception/reservations/{created['id']}",
        json=valid_payload(
            guest_id=2,
            room_id=2,
            check_in_date=new_start.isoformat(),
            check_out_date=(new_start + timedelta(days=2)).isoformat(),
            guest_count=3,
        ),
    )

    assert response.status_code == 200
    assert response.json()["guest_name"] == "Bruno Alves"
    assert response.json()["room_number"] == "202"
    assert response.json()["guest_count"] == 3


def test_cancel_reservation_without_deleting_it(
    reservation_context: dict[str, object],
) -> None:
    client = login_receptionist(reservation_context)
    created = client.post("/reception/reservations", json=valid_payload()).json()

    response = client.post(f"/reception/reservations/{created['id']}/cancel")

    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"
    session_factory = reservation_context["session_factory"]
    with session_factory() as session:  # type: ignore[operator]
        stored = session.get(Reservation, created["id"])
        assert stored is not None
        assert stored.status == "CANCELLED"


def test_reject_invalid_checkout_date(
    reservation_context: dict[str, object],
) -> None:
    client = login_receptionist(reservation_context)
    start = date.today() + timedelta(days=10)

    response = client.post(
        "/reception/reservations",
        json=valid_payload(
            check_in_date=start.isoformat(),
            check_out_date=start.isoformat(),
        ),
    )

    assert response.status_code == 422


def test_reject_unknown_room(reservation_context: dict[str, object]) -> None:
    client = login_receptionist(reservation_context)

    response = client.post(
        "/reception/reservations",
        json=valid_payload(room_id=999_999),
    )

    assert response.status_code == 404
    assert "Quarto" in response.json()["detail"]


def test_reject_unknown_guest(reservation_context: dict[str, object]) -> None:
    client = login_receptionist(reservation_context)

    response = client.post(
        "/reception/reservations",
        json=valid_payload(guest_id=999_999),
    )

    assert response.status_code == 404
    assert "Hóspede" in response.json()["detail"]


def test_unauthenticated_user_cannot_access_reservations(
    reservation_context: dict[str, object],
) -> None:
    client = reservation_context["client"]
    assert isinstance(client, TestClient)

    page_response = client.get("/reception/reservations")
    create_response = client.post("/reception/reservations", json=valid_payload())

    assert page_response.status_code == 401
    assert create_response.status_code == 401


def test_non_reception_user_cannot_access_reservations(
    reservation_context: dict[str, object],
) -> None:
    client = reservation_context["client"]
    session_secret = reservation_context["session_secret"]
    assert isinstance(client, TestClient)
    assert isinstance(session_secret, str)
    encoded_session = base64.b64encode(json.dumps({"user_id": 2}).encode("utf-8"))
    signed_session = TimestampSigner(session_secret).sign(encoded_session).decode("utf-8")
    client.cookies.set("hospitalitysync_session", signed_session)

    response = client.get("/reception/reservations")

    assert response.status_code == 401


def test_database_exclusion_violation_becomes_reservation_conflict(
    reservation_context: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_factory = reservation_context["session_factory"]

    class ExclusionViolation(Exception):
        sqlstate = "23P01"

    with session_factory() as session:  # type: ignore[operator]
        repository = ReservationRepository(session)
        service = ReservationService(repository)
        monkeypatch.setattr(repository, "has_overlapping_reservation", lambda **_: False)
        monkeypatch.setattr(
            repository,
            "commit",
            lambda: (_ for _ in ()).throw(
                IntegrityError("insert reservation", {}, ExclusionViolation())
            ),
        )
        payload = ReservationWriteRequest.model_validate(valid_payload())

        with pytest.raises(ReservationConflictError):
            service.create(payload)
