from __future__ import annotations

import secrets
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from tests.helpers import create_test_database


@pytest.fixture
def demo_client() -> Generator[TestClient, None, None]:
    engine, session_factory = create_test_database()
    app = create_app(
        settings=Settings(
            database_url="postgresql+psycopg://unused:unused@localhost/unused",
            session_secret_key=secrets.token_urlsafe(48),
            session_cookie_secure=False,
            enable_demo_access=True,
        ),
        session_factory=session_factory,
    )
    with TestClient(app) as client:
        yield client
    engine.dispose()


@pytest.mark.parametrize(
    ("area", "destination"),
    (("reception", "/reception"), ("kitchen", "/kitchen")),
)
def test_demo_employee_access_creates_authorized_session(
    demo_client: TestClient, area: str, destination: str
) -> None:
    response = demo_client.post(f"/auth/demo/{area}")
    assert response.status_code == 200
    assert response.json() == {"destination": destination}
    page = demo_client.get(destination)
    assert page.status_code == 200
    assert "Demonstração" in page.text


def test_demo_guest_access_is_bound_to_demo_room(demo_client: TestClient) -> None:
    response = demo_client.post("/auth/demo/guest")
    assert response.status_code == 200
    assert response.json() == {"destination": "/guest"}
    cookie = response.headers["set-cookie"].lower()
    assert "hospitalitysync_device=" in cookie
    assert "httponly" in cookie
    assert "path=/guest" in cookie
    page = demo_client.get("/guest")
    assert page.status_code == 200
    assert "DEMO-101" in page.text
    assert "Hóspede Demonstração" in page.text
    menu = demo_client.get("/guest/food")
    assert menu.status_code == 200
    assert "Sanduíche Hospitality" in menu.text


def test_demo_access_is_idempotent(demo_client: TestClient) -> None:
    for _ in range(2):
        assert demo_client.post("/auth/demo/guest").status_code == 200
        assert demo_client.get("/guest").status_code == 200


def test_demo_buttons_are_only_rendered_when_enabled(
    demo_client: TestClient,
) -> None:
    assert 'data-demo-area="reception"' in demo_client.get("/").text
    assert 'data-demo-area="guest"' in demo_client.get("/").text
    assert 'data-demo-area="kitchen"' in demo_client.get("/").text
    assert 'data-demo-area="reception"' in demo_client.get("/reception/login").text
    assert 'data-demo-area="kitchen"' in demo_client.get("/kitchen/login").text
    guest_required = demo_client.get("/guest", headers={"Accept": "text/html"})
    assert guest_required.status_code == 401
    assert 'data-demo-area="guest"' in guest_required.text


def test_demo_access_is_not_available_by_default() -> None:
    engine, session_factory = create_test_database()
    app = create_app(
        settings=Settings(
            database_url="postgresql+psycopg://unused:unused@localhost/unused",
            session_secret_key=secrets.token_urlsafe(48),
            session_cookie_secure=False,
        ),
        session_factory=session_factory,
    )
    with TestClient(app) as client:
        assert client.post("/auth/demo/reception").status_code == 404
        assert "data-demo-area" not in client.get("/").text
    engine.dispose()
