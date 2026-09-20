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
from app.models import Guest, Reservation, Room, RoomDevice, ServiceRequest, User
from tests.helpers import create_test_database


@pytest.fixture
def service_context() -> Generator[dict[str, object], None, None]:
    engine, session_factory = create_test_database()
    device_credential = secrets.token_urlsafe(48)
    second_credential = secrets.token_urlsafe(48)
    password = secrets.token_urlsafe(24)
    email = f"services-{secrets.token_hex(6)}@example.test"
    now = datetime.now(timezone.utc)
    with Session(engine) as session:
        session.add_all([
            User(id=1, name="Reception", email=email, password_hash=password_hasher.hash(password), role="RECEPTION", active=True),
            Guest(id=1, full_name="Service Guest", document="SERVICE-1"),
            Guest(id=2, full_name="Other Guest", document="SERVICE-2"),
            Room(id=1, number="501", category="Standard", capacity=2, status="OCCUPIED"),
            Room(id=2, number="502", category="Standard", capacity=2, status="OCCUPIED"),
            RoomDevice(id=1, room_id=1, code="ROOM-501", credential_hash=hash_device_credential(device_credential), active=True, provisioned_at=now),
            RoomDevice(id=2, room_id=2, code="ROOM-502", credential_hash=hash_device_credential(second_credential), active=True, provisioned_at=now),
            Reservation(id=1, guest_id=1, room_id=1, check_in_date=date.today(), check_out_date=date.today()+timedelta(days=2), guest_count=1, status="CHECKED_IN", actual_check_in_at=now-timedelta(hours=1)),
            Reservation(id=2, guest_id=2, room_id=2, check_in_date=date.today(), check_out_date=date.today()+timedelta(days=2), guest_count=1, status="CHECKED_IN", actual_check_in_at=now-timedelta(hours=1)),
        ])
        session.commit()
    app = create_app(
        settings=Settings(database_url="postgresql+psycopg://unused:unused@localhost/unused", session_secret_key=secrets.token_urlsafe(48), session_cookie_secure=False),
        session_factory=session_factory,
    )
    with TestClient(app) as client:
        yield {"client": client, "session_factory": session_factory, "credential": device_credential, "second_credential": second_credential, "credentials": {"email": email, "password": password}}
    engine.dispose()


def use_device(context: dict[str, object], credential_key: str = "credential") -> TestClient:
    client = context["client"]
    assert isinstance(client, TestClient)
    client.cookies.set("hospitalitysync_device", context[credential_key], path="/guest")
    return client


def login_reception(context: dict[str, object]) -> TestClient:
    client = context["client"]
    assert isinstance(client, TestClient)
    assert client.post("/auth/login", json=context["credentials"]).status_code == 200
    return client


@pytest.mark.parametrize("category", ["CLEANING", "MAINTENANCE", "HELP", "COMPLAINT"])
def test_room_device_creates_supported_service_requests(service_context: dict[str, object], category: str) -> None:
    response = use_device(service_context).post("/guest/service-requests", json={"category": category, "description": f"Request for {category}"})
    assert response.status_code == 201
    assert response.json()["room_number"] == "501"
    assert response.json()["status"] == "OPEN"
    session_factory = service_context["session_factory"]
    with session_factory() as session:  # type: ignore[operator]
        item = session.get(ServiceRequest, response.json()["id"])
        assert item is not None
        assert item.room_id == 1 and item.reservation_id == 1 and item.room_device_id == 1


def test_invalid_category_and_description_are_rejected(service_context: dict[str, object]) -> None:
    client = use_device(service_context)
    assert client.post("/guest/service-requests", json={"category": "OTHER", "description": "Valid text"}).status_code == 422
    assert client.post("/guest/service-requests", json={"category": "HELP", "description": "  "}).status_code == 422


def test_active_stay_is_required(service_context: dict[str, object]) -> None:
    session_factory = service_context["session_factory"]
    with session_factory() as session:  # type: ignore[operator]
        reservation = session.get(Reservation, 1)
        assert reservation is not None
        reservation.status = "CHECKED_OUT"
        reservation.actual_check_out_at = datetime.now(timezone.utc)
        session.commit()
    response = use_device(service_context).post("/guest/service-requests", json={"category": "HELP", "description": "Need assistance"})
    assert response.status_code == 409


def test_history_is_isolated_by_current_room_and_stay(service_context: dict[str, object]) -> None:
    client = use_device(service_context)
    assert client.post("/guest/service-requests", json={"category": "CLEANING", "description": "Room 501 request"}).status_code == 201
    client.cookies.set("hospitalitysync_device", service_context["second_credential"], path="/guest")
    assert client.post("/guest/service-requests", json={"category": "HELP", "description": "Secret room 502 request"}).status_code == 201
    client.cookies.set("hospitalitysync_device", service_context["credential"], path="/guest")
    response = client.get("/guest/service-requests")
    assert response.status_code == 200
    assert [item["description"] for item in response.json()] == ["Room 501 request"]


def test_reception_advances_status_and_completed_timestamp(service_context: dict[str, object]) -> None:
    created = use_device(service_context).post("/guest/service-requests", json={"category": "MAINTENANCE", "description": "Air conditioner"}).json()
    client = login_reception(service_context)
    started = client.post(f"/reception/service-requests/{created['id']}/status", json={"status": "IN_PROGRESS"})
    completed = client.post(f"/reception/service-requests/{created['id']}/status", json={"status": "COMPLETED"})
    assert started.status_code == 200
    assert completed.status_code == 200
    assert completed.json()["completed_at"] is not None


def test_invalid_status_transition_and_missing_request(service_context: dict[str, object]) -> None:
    created = use_device(service_context).post("/guest/service-requests", json={"category": "HELP", "description": "Need help"}).json()
    client = login_reception(service_context)
    assert client.post(f"/reception/service-requests/{created['id']}/status", json={"status": "COMPLETED"}).status_code == 409
    assert client.post("/reception/service-requests/999/status", json={"status": "IN_PROGRESS"}).status_code == 404


def test_service_routes_enforce_authentication(service_context: dict[str, object]) -> None:
    client = service_context["client"]
    assert isinstance(client, TestClient)
    assert client.get("/guest/service-requests").status_code == 401
    assert client.get("/reception/service-requests").status_code == 401


def test_reception_receives_service_request_over_websocket(service_context: dict[str, object]) -> None:
    client=login_reception(service_context)
    with client.websocket_connect("/reception/ws") as websocket:
        response=use_device(service_context).post("/guest/service-requests",json={"category":"HELP","description":"Realtime help"})
        assert response.status_code==201
        event=websocket.receive_json()
    assert event=={"type":"service_request.created","id":response.json()["id"]}
