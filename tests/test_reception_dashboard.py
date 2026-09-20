from __future__ import annotations

import secrets
from collections.abc import Generator
from datetime import date, datetime, time, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import password_hasher
from app.main import create_app
from app.models import FoodOrder, Guest, Reservation, Room, RoomDevice, ServiceRequest, User
from tests.helpers import create_test_database


@pytest.fixture
def dashboard_client() -> Generator[tuple[TestClient, dict[str, str]], None, None]:
    engine, session_factory = create_test_database()
    password = secrets.token_urlsafe(24)
    email = f"dashboard-{secrets.token_hex(8)}@example.test"
    password_hash = password_hasher.hash(password)
    today = date.today()
    check_in_timestamp = datetime.combine(
        today - timedelta(days=1),
        time(hour=14),
        tzinfo=timezone.utc,
    )

    with Session(engine) as session:
        session.add(
            User(
                id=1,
                name="Ana Recepção",
                email=email,
                password_hash=password_hash,
                role="RECEPTION",
                active=True,
            )
        )
        session.add_all(
            [
                Room(
                    id=1,
                    number="101",
                    category="Standard",
                    capacity=2,
                    status="OCCUPIED",
                    active=True,
                ),
                Room(
                    id=2,
                    number="102",
                    category="Suíte",
                    capacity=3,
                    status="AVAILABLE",
                    active=True,
                ),
                Room(
                    id=3,
                    number="103",
                    category="Standard",
                    capacity=2,
                    status="OCCUPIED",
                    active=True,
                ),
                Room(
                    id=4,
                    number="104",
                    category="Standard",
                    capacity=2,
                    status="AVAILABLE",
                    active=False,
                ),
            ]
        )
        session.add_all(
            [
                Guest(
                    id=1,
                    full_name="Marina Costa",
                    document="sensitive-document-one",
                    active=True,
                ),
                Guest(
                    id=2,
                    full_name="Rafael Nunes",
                    document="sensitive-document-two",
                    active=True,
                ),
                Guest(
                    id=3,
                    full_name="Clara Lima",
                    document="sensitive-document-three",
                    active=True,
                ),
            ]
        )
        session.flush()
        session.add_all(
            [
                Reservation(
                    id=1,
                    guest_id=1,
                    room_id=1,
                    check_in_date=today - timedelta(days=1),
                    check_out_date=today + timedelta(days=1),
                    guest_count=2,
                    status="CHECKED_IN",
                    actual_check_in_at=check_in_timestamp,
                ),
                Reservation(
                    id=2,
                    guest_id=2,
                    room_id=2,
                    check_in_date=today,
                    check_out_date=today + timedelta(days=2),
                    guest_count=1,
                    status="CONFIRMED",
                ),
                Reservation(
                    id=3,
                    guest_id=3,
                    room_id=3,
                    check_in_date=today - timedelta(days=1),
                    check_out_date=today,
                    guest_count=1,
                    status="CHECKED_IN",
                    actual_check_in_at=check_in_timestamp,
                ),
            ]
        )
        session.flush()
        session.add(
            RoomDevice(
                id=1,
                room_id=1,
                code="DASH-101",
                credential_hash="a" * 64,
                active=True,
                provisioned_at=datetime.now(timezone.utc),
            )
        )
        session.add_all(
            [
                ServiceRequest(room_id=1, reservation_id=1, created_by_user_id=1, category="CLEANING", status="OPEN", description="Clean room"),
                ServiceRequest(room_id=1, reservation_id=1, created_by_user_id=1, category="COMPLAINT", status="OPEN", description="Complaint"),
                ServiceRequest(room_id=1, reservation_id=1, created_by_user_id=1, category="HELP", status="IN_PROGRESS", description="Help"),
                FoodOrder(reservation_id=1, room_device_id=1, status="READY"),
            ]
        )
        session.commit()

    settings = Settings(
        database_url="postgresql+psycopg://unused:unused@localhost/unused",
        session_secret_key=secrets.token_urlsafe(48),
        session_cookie_secure=False,
    )
    app = create_app(settings=settings, session_factory=session_factory)

    with TestClient(app) as test_client:
        yield test_client, {
            "email": email,
            "password": password,
            "password_hash": password_hash,
        }

    engine.dispose()


def test_dashboard_displays_data_from_database(
    dashboard_client: tuple[TestClient, dict[str, str]],
) -> None:
    client, credentials = dashboard_client
    login_response = client.post(
        "/auth/login",
        json={"email": credentials["email"], "password": credentials["password"]},
    )
    assert login_response.status_code == 200

    response = client.get("/reception")

    assert response.status_code == 200
    assert 'data-testid="occupied-rooms-count">2<' in response.text
    assert 'data-testid="available-rooms-count">1<' in response.text
    assert 'data-testid="reservations-today-count">3<' in response.text
    assert 'data-testid="expected-check-ins-count">1<' in response.text
    assert 'data-testid="expected-check-outs-count">1<' in response.text
    assert 'data-testid="cleaning-requests-count">1<' in response.text
    assert 'data-testid="maintenance-requests-count">0<' in response.text
    assert 'data-testid="complaints-count">1<' in response.text
    assert 'data-testid="help-requests-count">1<' in response.text
    assert 'data-testid="active-food-orders-count">1<' in response.text
    assert 'data-room-number="101"' in response.text
    assert 'data-room-number="102"' in response.text
    assert 'data-room-number="103"' in response.text
    assert 'data-room-number="104"' not in response.text
    assert "Marina Costa" in response.text
    assert "Rafael Nunes" in response.text
    assert "Clara Lima" in response.text


def test_dashboard_does_not_expose_sensitive_information(
    dashboard_client: tuple[TestClient, dict[str, str]],
) -> None:
    client, credentials = dashboard_client
    client.post(
        "/auth/login",
        json={"email": credentials["email"], "password": credentials["password"]},
    )

    response = client.get("/reception")

    assert credentials["password"] not in response.text
    assert credentials["password_hash"] not in response.text
    assert "sensitive-document-one" not in response.text
    assert "sensitive-document-two" not in response.text
    assert "sensitive-document-three" not in response.text
