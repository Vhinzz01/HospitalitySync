from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.exception_handlers import http_exception_handler
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy import Engine
from starlette.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import Settings
from app.database.connection import SessionFactory, create_session_factory
from app.routers.auth import router as auth_router
from app.routers.guest import router as guest_router
from app.routers.kitchen import router as kitchen_router
from app.routers.realtime import router as realtime_router
from app.routers.reception import router as reception_router
from app.routers.reception_guests import router as reception_guests_router
from app.routers.reception_devices import router as reception_devices_router
from app.routers.reception_reservations import router as reception_reservations_router
from app.routers.reception_stays import router as reception_stays_router
from app.routers.reception_service_requests import (
    router as reception_service_requests_router,
)


STATIC_DIRECTORY = Path(__file__).resolve().parent / "static"
templates = Jinja2Templates(directory=str(STATIC_DIRECTORY.parent / "templates"))


def create_app(
    settings: Settings | None = None,
    session_factory: SessionFactory | None = None,
) -> FastAPI:
    application_settings = settings or Settings.from_environment()
    owned_engine: Engine | None = None

    if session_factory is None:
        owned_engine, session_factory = create_session_factory(
            application_settings.database_url
        )

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield
        if owned_engine is not None:
            owned_engine.dispose()

    app = FastAPI(title="HospitalitySync", lifespan=lifespan)
    app.state.settings = application_settings
    app.state.session_factory = session_factory

    @app.exception_handler(StarletteHTTPException)
    async def browser_access_error(request: Request, error: StarletteHTTPException):
        # Preserve API status/contracts; only browser HTML requests get a visual page.
        area = request.url.path.split("/")[1]
        if (
            error.status_code in {401, 403}
            and "text/html" in request.headers.get("accept", "")
            and area in {"reception", "guest", "kitchen"}
        ):
            return templates.TemplateResponse(
                request=request,
                name="access-required.html",
                context={
                    "area": area,
                    "demo_access_enabled": application_settings.enable_demo_access,
                },
                status_code=error.status_code,
                headers=error.headers,
            )
        return await http_exception_handler(request, error)

    app.add_middleware(
        SessionMiddleware,
        secret_key=application_settings.session_secret_key,
        session_cookie="hospitalitysync_session",
        max_age=application_settings.session_max_age_seconds,
        same_site="lax",
        https_only=application_settings.session_cookie_secure,
    )

    @app.middleware("http")
    async def browser_security(request: Request, call_next):
        origin = request.headers.get("origin")
        if (
            request.method in {"POST", "PUT", "PATCH", "DELETE"}
            and origin
            and origin.rstrip("/") != str(request.base_url).rstrip("/")
        ):
            return JSONResponse(
                status_code=403,
                content={"detail": "Cross-origin request blocked."},
            )
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        if request.url.path.startswith("/docs") or request.url.path == "/redoc":
            content_security_policy = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "img-src 'self' data: https://fastapi.tiangolo.com; "
                "connect-src 'self'; frame-ancestors 'none'"
            )
        else:
            content_security_policy = (
                "default-src 'self'; script-src 'self'; style-src 'self'; "
                "img-src 'self' data:; connect-src 'self' ws: wss:; "
                "frame-ancestors 'none'"
            )
        response.headers.setdefault(
            "Content-Security-Policy",
            content_security_policy,
        )
        if application_settings.session_cookie_secure:
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return response

    @app.get("/", include_in_schema=False)
    def root(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request=request,
            name="landing.html",
            context={"demo_access_enabled": application_settings.enable_demo_access},
        )

    app.mount("/static", StaticFiles(directory=str(STATIC_DIRECTORY)), name="static")
    app.include_router(auth_router)
    app.include_router(reception_router)
    app.include_router(reception_guests_router)
    app.include_router(reception_reservations_router)
    app.include_router(reception_stays_router)
    app.include_router(reception_devices_router)
    app.include_router(reception_service_requests_router)
    app.include_router(guest_router)
    app.include_router(kitchen_router)
    app.include_router(realtime_router)
    return app
