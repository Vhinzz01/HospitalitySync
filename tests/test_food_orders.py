from __future__ import annotations

import secrets
from collections.abc import Generator
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import hash_device_credential, password_hasher
from app.main import create_app
from app.models import FoodOrder, Guest, MenuItem, Reservation, Room, RoomDevice, User
from tests.helpers import create_test_database


@pytest.fixture
def food_context() -> Generator[dict[str, object], None, None]:
    engine, session_factory = create_test_database()
    kitchen_password = secrets.token_urlsafe(20)
    kitchen_email = f"kitchen-{secrets.token_hex(6)}@example.test"
    reception_password = secrets.token_urlsafe(20)
    reception_email = f"reception-{secrets.token_hex(6)}@example.test"
    credential = secrets.token_urlsafe(48)
    other_credential = secrets.token_urlsafe(48)
    now = datetime.now(timezone.utc)
    with Session(engine) as session:
        session.add_all([
            User(id=1,name="Kitchen",email=kitchen_email,password_hash=password_hasher.hash(kitchen_password),role="KITCHEN",active=True),
            User(id=2,name="Reception",email=reception_email,password_hash=password_hasher.hash(reception_password),role="RECEPTION",active=True),
            Guest(id=1,full_name="Food Guest",document="FOOD-1"), Guest(id=2,full_name="Other Food Guest",document="FOOD-2"),
            Room(id=1,number="601",category="Suite",capacity=2,status="OCCUPIED"), Room(id=2,number="602",category="Standard",capacity=2,status="OCCUPIED"),
            RoomDevice(id=1,room_id=1,code="ROOM-601",credential_hash=hash_device_credential(credential),active=True,provisioned_at=now),
            RoomDevice(id=2,room_id=2,code="ROOM-602",credential_hash=hash_device_credential(other_credential),active=True,provisioned_at=now),
            Reservation(id=1,guest_id=1,room_id=1,check_in_date=date.today(),check_out_date=date.today()+timedelta(days=2),guest_count=1,status="CHECKED_IN",actual_check_in_at=now-timedelta(hours=1)),
            Reservation(id=2,guest_id=2,room_id=2,check_in_date=date.today(),check_out_date=date.today()+timedelta(days=2),guest_count=1,status="CHECKED_IN",actual_check_in_at=now-timedelta(hours=1)),
            MenuItem(id=1,name="Club Sandwich",description="Sandwich",price=Decimal("25.50"),available=True),
            MenuItem(id=2,name="Soup",description="Soup",price=Decimal("18.00"),available=False),
        ])
        session.commit()
    app=create_app(settings=Settings(database_url="postgresql+psycopg://unused:unused@localhost/unused",session_secret_key=secrets.token_urlsafe(48),session_cookie_secure=False),session_factory=session_factory)
    with TestClient(app) as client:
        yield {"client":client,"session_factory":session_factory,"credential":credential,"other_credential":other_credential,"kitchen":{"email":kitchen_email,"password":kitchen_password},"reception":{"email":reception_email,"password":reception_password}}
    engine.dispose()


def device_client(context: dict[str, object], key: str = "credential") -> TestClient:
    client=context["client"]; assert isinstance(client,TestClient)
    client.cookies.set("hospitalitysync_device",context[key],path="/guest")
    return client


def kitchen_client(context: dict[str, object]) -> TestClient:
    client=context["client"]; assert isinstance(client,TestClient)
    assert client.post("/auth/kitchen/login",json=context["kitchen"]).status_code==200
    return client


def create_order(context: dict[str, object], quantity: int = 2) -> dict:
    response=device_client(context).post("/guest/orders",json={"items":[{"menu_item_id":1,"quantity":quantity}],"notes":"No onions"})
    assert response.status_code==201
    return response.json()


def test_kitchen_login_and_role_protection(food_context: dict[str, object]) -> None:
    client=food_context["client"]; assert isinstance(client,TestClient)
    assert client.get("/kitchen").status_code==401
    assert client.post("/auth/kitchen/login",json=food_context["kitchen"]).status_code==200
    assert client.get("/kitchen").status_code==200
    client.post("/auth/logout")
    # Reception credentials cannot authenticate on the kitchen login endpoint.
    assert client.post("/auth/kitchen/login",json=food_context["reception"]).status_code==401
    assert client.post("/auth/login",json=food_context["reception"]).status_code==200
    assert client.get("/kitchen").status_code==403


def test_kitchen_manages_menu(food_context: dict[str, object]) -> None:
    client=kitchen_client(food_context)
    created=client.post("/kitchen/menu-items",json={"name":"Salad","description":"Fresh","price":"16.90","available":True})
    assert created.status_code==201
    item_id=created.json()["id"]
    updated=client.put(f"/kitchen/menu-items/{item_id}",json={"name":"Green Salad","description":None,"price":"17.50","available":True})
    paused=client.post(f"/kitchen/menu-items/{item_id}/availability",json={"available":False})
    assert updated.json()["name"]=="Green Salad"
    assert paused.json()["available"] is False


def test_order_uses_price_snapshot_and_calculates_total(food_context: dict[str, object]) -> None:
    payload=create_order(food_context,3)
    assert Decimal(payload["items"][0]["unit_price"])==Decimal("25.50")
    assert Decimal(payload["total"])==Decimal("76.50")
    session_factory=food_context["session_factory"]
    with session_factory() as session:  # type: ignore[operator]
        item=session.get(MenuItem,1); assert item is not None; item.price=Decimal("99.00"); session.commit()
    orders=device_client(food_context).get("/guest/orders").json()
    assert Decimal(orders[0]["total"])==Decimal("76.50")


def test_unavailable_missing_and_duplicate_items_are_rejected(food_context: dict[str, object]) -> None:
    client=device_client(food_context)
    assert client.post("/guest/orders",json={"items":[{"menu_item_id":2,"quantity":1}]}).status_code==409
    assert client.post("/guest/orders",json={"items":[{"menu_item_id":999,"quantity":1}]}).status_code==404
    assert client.post("/guest/orders",json={"items":[{"menu_item_id":1,"quantity":1},{"menu_item_id":1,"quantity":2}]}).status_code==400


def test_active_stay_required_for_order(food_context: dict[str, object]) -> None:
    session_factory=food_context["session_factory"]
    with session_factory() as session:  # type: ignore[operator]
        stay=session.get(Reservation,1); assert stay is not None; stay.status="CHECKED_OUT"; stay.actual_check_out_at=datetime.now(timezone.utc); session.commit()
    assert device_client(food_context).post("/guest/orders",json={"items":[{"menu_item_id":1,"quantity":1}]}).status_code==409


def test_order_history_is_isolated_between_rooms(food_context: dict[str, object]) -> None:
    create_order(food_context)
    client=device_client(food_context,"other_credential")
    assert client.get("/guest/orders").json()==[]


def test_kitchen_order_status_follows_sequence(food_context: dict[str, object]) -> None:
    order=create_order(food_context)
    client=kitchen_client(food_context)
    for next_status in ("PREPARING","READY","DELIVERED"):
        response=client.post(f"/kitchen/orders/{order['id']}/status",json={"status":next_status})
        assert response.status_code==200 and response.json()["status"]==next_status
    assert response.json()["delivered_at"] is not None


def test_kitchen_rejects_skipped_status_and_missing_order(food_context: dict[str, object]) -> None:
    order=create_order(food_context)
    client=kitchen_client(food_context)
    assert client.post(f"/kitchen/orders/{order['id']}/status",json={"status":"READY"}).status_code==409
    assert client.post("/kitchen/orders/999/status",json={"status":"PREPARING"}).status_code==404


def test_guest_food_routes_require_device(food_context: dict[str, object]) -> None:
    client=food_context["client"]; assert isinstance(client,TestClient)
    assert client.get("/guest/menu").status_code==401
    assert client.post("/guest/orders",json={"items":[{"menu_item_id":1,"quantity":1}]}).status_code==401


def test_kitchen_receives_new_order_over_websocket(food_context: dict[str, object]) -> None:
    client=kitchen_client(food_context)
    with client.websocket_connect("/kitchen/ws") as websocket:
        order=create_order(food_context)
        event=websocket.receive_json()
    assert event=={"type":"food_order.created","id":order["id"]}


def test_guest_receives_order_status_only_for_its_room(food_context: dict[str, object]) -> None:
    order=create_order(food_context)
    client=kitchen_client(food_context)
    client.cookies.set("hospitalitysync_device",food_context["credential"],path="/guest")
    with client.websocket_connect("/guest/ws") as websocket:
        response=client.post(f"/kitchen/orders/{order['id']}/status",json={"status":"PREPARING"})
        assert response.status_code==200
        event=websocket.receive_json()
    assert event=={"type":"food_order.updated","id":order["id"],"status":"PREPARING"}
