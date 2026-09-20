from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.routers.dependencies import ReceptionDashboard, ReceptionUser
from app.schemas import ReceptionUserResponse


TEMPLATES_DIRECTORY = Path(__file__).resolve().parents[1] / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIRECTORY))


router = APIRouter(prefix="/reception", tags=["reception"])


@router.get("", response_class=HTMLResponse)
def reception_area(
    request: Request,
    current_user: ReceptionUser,
    dashboard_service: ReceptionDashboard,
) -> HTMLResponse:
    dashboard = dashboard_service.build_dashboard()
    safe_user = ReceptionUserResponse.model_validate(current_user)
    return templates.TemplateResponse(
        request=request,
        name="reception/dashboard.html",
        context={"dashboard": dashboard, "user": safe_user},
    )
