from __future__ import annotations

import secrets
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from starlette.websockets import WebSocketDisconnect

from app.core.config import Settings
from app.core.security import password_hasher
from app.main import create_app
from app.models import User
from tests.helpers import create_test_database


@pytest.fixture
def security_context() -> Generator[dict[str, object], None, None]:
    engine, session_factory = create_test_database()
    reception_password = secrets.token_urlsafe(20)
    kitchen_password = secrets.token_urlsafe(20)
    reception_email = f"security-reception-{secrets.token_hex(5)}@example.test"
    kitchen_email = f"security-kitchen-{secrets.token_hex(5)}@example.test"
    with Session(engine) as session:
        session.add_all([
            User(id=1,name="Reception",email=reception_email,password_hash=password_hasher.hash(reception_password),role="RECEPTION",active=True),
            User(id=2,name="Kitchen",email=kitchen_email,password_hash=password_hasher.hash(kitchen_password),role="KITCHEN",active=True),
        ])
        session.commit()
    app=create_app(settings=Settings(database_url="postgresql+psycopg://unused:unused@localhost/unused",session_secret_key=secrets.token_urlsafe(48),session_cookie_secure=False),session_factory=session_factory)
    with TestClient(app) as client:
        yield {"client":client,"reception":{"email":reception_email,"password":reception_password},"kitchen":{"email":kitchen_email,"password":kitchen_password}}
    engine.dispose()


def test_security_headers_are_applied(security_context: dict[str, object]) -> None:
    client=security_context["client"]; assert isinstance(client,TestClient)
    response=client.get("/kitchen/login")
    assert response.headers["x-content-type-options"]=="nosniff"
    assert response.headers["x-frame-options"]=="DENY"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]


def test_root_serves_landing_page(
    security_context: dict[str, object],
) -> None:
    client=security_context["client"]; assert isinstance(client,TestClient)
    response=client.get("/",follow_redirects=False)
    assert response.status_code==200
    assert 'href="/reception/login"' in response.text
    assert 'href="/kitchen/login"' in response.text
    assert 'href="/guest"' in response.text
    assert "A arte de receber." in response.text
    assert "'unsafe-inline'" not in response.headers["content-security-policy"]


def test_reception_login_uses_existing_authentication(security_context):
    client = security_context["client"]
    page = client.get("/reception/login")
    assert page.status_code == 200
    assert 'data-endpoint="/auth/login"' in page.text
    assert 'data-destination="/reception"' in page.text
    assert client.get("/reception").status_code == 401
    assert client.post("/auth/login", json=security_context["reception"]).status_code == 200
    assert client.get("/reception").status_code == 200
    assert client.post("/auth/logout").status_code == 204
    assert client.get("/reception").status_code == 401


def test_kitchen_login_uses_existing_authentication(security_context):
    client = security_context["client"]
    page = client.get("/kitchen/login")
    assert page.status_code == 200
    assert 'data-endpoint="/auth/kitchen/login"' in page.text
    assert client.post("/auth/kitchen/login", json=security_context["kitchen"]).status_code == 200
    page = client.get("/kitchen")
    assert page.status_code == 200
    assert page.text.count('class="order-column"') == 4


def test_api_documentation_csp_allows_swagger_assets(
    security_context: dict[str, object],
) -> None:
    client=security_context["client"]; assert isinstance(client,TestClient)
    response=client.get("/docs")
    policy=response.headers["content-security-policy"]
    assert response.status_code==200
    assert "https://cdn.jsdelivr.net" in policy
    assert "'unsafe-inline'" in policy


@pytest.mark.parametrize("path,link", [
    ("/reception", "/reception/login"),
    ("/kitchen", "/kitchen/login"),
    ("/guest", "/guest/setup"),
])
def test_html_access_error_preserves_authorization(security_context, path, link):
    client = security_context["client"]
    response = client.get(path, headers={"Accept": "text/html"})
    assert response.status_code == 401
    assert f'href="{link}"' in response.text
    api_response = client.get(path, headers={"Accept": "application/json"})
    assert api_response.status_code == 401
    assert "detail" in api_response.json()


def test_cross_origin_state_change_is_blocked(security_context: dict[str, object]) -> None:
    client=security_context["client"]; assert isinstance(client,TestClient)
    response=client.post("/auth/login",json=security_context["reception"],headers={"Origin":"https://attacker.example"})
    assert response.status_code==403


def test_employee_roles_cannot_cross_operational_areas(security_context: dict[str, object]) -> None:
    client=security_context["client"]; assert isinstance(client,TestClient)
    assert client.post("/auth/login",json=security_context["reception"]).status_code==200
    assert client.get("/kitchen").status_code==403
    client.post("/auth/logout")
    assert client.post("/auth/kitchen/login",json=security_context["kitchen"]).status_code==200
    assert client.get("/reception").status_code==401


def test_websocket_rejects_external_origin(security_context: dict[str, object]) -> None:
    client=security_context["client"]; assert isinstance(client,TestClient)
    assert client.post("/auth/kitchen/login",json=security_context["kitchen"]).status_code==200
    with pytest.raises(WebSocketDisconnect) as error:
        with client.websocket_connect("/kitchen/ws",headers={"Origin":"https://attacker.example"}):
            pass
    assert error.value.code==4403
