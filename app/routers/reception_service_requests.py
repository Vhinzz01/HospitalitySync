from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.routers.dependencies import ReceptionUser, ServiceRequests
from app.schemas import (
    ReceptionUserResponse,
    ServiceRequestStatusUpdate,
    ServiceRequestView,
)
from app.services import ServiceRequestNotFoundError, ServiceRequestStateError
from app.realtime import realtime_hub


TEMPLATES_DIRECTORY = Path(__file__).resolve().parents[1] / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIRECTORY))
router = APIRouter(prefix="/reception/service-requests", tags=["reception-services"])


def _raise_http_error(error: Exception) -> None:
    if isinstance(error, ServiceRequestNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    if isinstance(error, ServiceRequestStateError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    raise error


@router.get("", response_class=HTMLResponse)
def service_requests_page(
    request: Request,
    current_user: ReceptionUser,
    service: ServiceRequests,
    category: str | None = Query(default=None),
    request_status: str | None = Query(default=None, alias="status"),
) -> HTMLResponse:
    try:
        requests = service.list_for_reception(category, request_status)
    except ServiceRequestStateError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    return templates.TemplateResponse(
        request=request,
        name="reception/services/list.html",
        context={
            "user": ReceptionUserResponse.model_validate(current_user),
            "requests": requests,
            "filters": {"category": category or "", "status": request_status or ""},
        },
    )


@router.post("/{request_id}/status", response_model=ServiceRequestView)
def update_service_request_status(
    request_id: int,
    payload: ServiceRequestStatusUpdate,
    _: ReceptionUser,
    service: ServiceRequests,
    background_tasks: BackgroundTasks,
) -> ServiceRequestView:
    try:
        result = service.update_status(request_id, payload)
        room_id = service.get_room_id(request_id)
        if room_id is not None:
            background_tasks.add_task(
                realtime_hub.notify_guest,
                room_id,
                {"type": "service_request.updated", "id": result.id, "status": result.status},
            )
        return result
    except (ServiceRequestNotFoundError, ServiceRequestStateError) as error:
        _raise_http_error(error)
