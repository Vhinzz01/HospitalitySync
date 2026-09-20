from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.routers.dependencies import ReceptionDashboard, ReceptionUser, ServiceRequests
from app.schemas import ReceptionUserResponse


TEMPLATES_DIRECTORY = Path(__file__).resolve().parents[1] / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIRECTORY))


router = APIRouter(prefix="/reception", tags=["reception"])


@router.get("/login", response_class=HTMLResponse, include_in_schema=False)
def reception_login_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="reception/login.html",
        context={"demo_access_enabled": request.app.state.settings.enable_demo_access},
    )


@router.get("", response_class=HTMLResponse)
def reception_area(
    request: Request,
    current_user: ReceptionUser,
    dashboard_service: ReceptionDashboard,
    request_service: ServiceRequests,
) -> HTMLResponse:
    dashboard = dashboard_service.build_dashboard()
    safe_user = ReceptionUserResponse.model_validate(current_user)
    return templates.TemplateResponse(
        request=request,
        name="reception/dashboard.html",
        context={
            "dashboard": dashboard,
            "user": safe_user,
            "recent_requests": request_service.list_for_reception()[:8],
        },
    )
