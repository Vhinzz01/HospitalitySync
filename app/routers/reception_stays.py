from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.routers.dependencies import ReceptionUser, Stays
from app.schemas import ReceptionUserResponse, StayOperationView
from app.services import StayNotFoundError, StayStateConflictError


TEMPLATES_DIRECTORY = Path(__file__).resolve().parents[1] / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIRECTORY))
router = APIRouter(prefix="/reception", tags=["reception-stays"])


def _raise_http_error(error: Exception) -> None:
    if isinstance(error, StayNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    if isinstance(error, StayStateConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    raise error


@router.get("/check-in", response_class=HTMLResponse)
def check_in_page(
    request: Request,
    current_user: ReceptionUser,
    service: Stays,
) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="reception/stays/operations.html",
        context={
            "user": ReceptionUserResponse.model_validate(current_user),
            "records": service.list_expected_check_ins(),
            "operation": "check-in",
            "title": "Check-in",
            "description": "Reservas confirmadas aguardando a chegada do hóspede.",
            "empty_message": "Nenhum check-in aguardando realização.",
        },
    )


@router.get("/check-out", response_class=HTMLResponse)
def check_out_page(
    request: Request,
    current_user: ReceptionUser,
    service: Stays,
) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="reception/stays/operations.html",
        context={
            "user": ReceptionUserResponse.model_validate(current_user),
            "records": service.list_active_stays(),
            "operation": "check-out",
            "title": "Check-out",
            "description": "Hospedagens ativas prontas para finalização.",
            "empty_message": "Nenhuma hospedagem ativa para check-out.",
        },
    )


@router.post(
    "/reservations/{reservation_id}/check-in",
    response_model=StayOperationView,
)
def perform_check_in(
    reservation_id: int,
    _: ReceptionUser,
    service: Stays,
) -> StayOperationView:
    try:
        return service.check_in(reservation_id)
    except (StayNotFoundError, StayStateConflictError) as error:
        _raise_http_error(error)


@router.post(
    "/reservations/{reservation_id}/check-out",
    response_model=StayOperationView,
)
def perform_check_out(
    reservation_id: int,
    _: ReceptionUser,
    service: Stays,
) -> StayOperationView:
    try:
        return service.check_out(reservation_id)
    except (StayNotFoundError, StayStateConflictError) as error:
        _raise_http_error(error)
