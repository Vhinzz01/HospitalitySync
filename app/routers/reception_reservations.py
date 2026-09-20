from __future__ import annotations

from datetime import date
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.routers.dependencies import ReceptionUser, Reservations
from app.schemas import ReceptionUserResponse, ReservationView, ReservationWriteRequest
from app.services import (
    GuestNotFoundError,
    ReservationConflictError,
    ReservationNotFoundError,
    ReservationStateError,
    ReservationValidationError,
    RoomNotFoundError,
)


TEMPLATES_DIRECTORY = Path(__file__).resolve().parents[1] / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIRECTORY))
router = APIRouter(prefix="/reception/reservations", tags=["reception-reservations"])


def _safe_user(user: ReceptionUser) -> ReceptionUserResponse:
    return ReceptionUserResponse.model_validate(user)


def _raise_http_error(error: Exception) -> None:
    if isinstance(error, (ReservationNotFoundError, GuestNotFoundError, RoomNotFoundError)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    if isinstance(error, (ReservationConflictError, ReservationStateError)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    if isinstance(error, ReservationValidationError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))
    raise error


@router.get("", response_class=HTMLResponse)
def reservations_page(
    request: Request,
    current_user: ReceptionUser,
    service: Reservations,
    reservation_status: str | None = Query(default=None, alias="status"),
    period_start: date | None = Query(default=None),
    period_end: date | None = Query(default=None),
) -> HTMLResponse:
    try:
        reservations = service.list_reservations(
            status=reservation_status,
            period_start=period_start,
            period_end=period_end,
        )
    except ReservationValidationError as error:
        _raise_http_error(error)

    return templates.TemplateResponse(
        request=request,
        name="reception/reservations/list.html",
        context={
            "user": _safe_user(current_user),
            "reservations": reservations,
            "filters": {
                "status": reservation_status or "",
                "period_start": period_start.isoformat() if period_start else "",
                "period_end": period_end.isoformat() if period_end else "",
            },
        },
    )


@router.get("/new", response_class=HTMLResponse)
def new_reservation_page(
    request: Request,
    current_user: ReceptionUser,
    service: Reservations,
) -> HTMLResponse:
    form_data = service.get_form_data()
    return templates.TemplateResponse(
        request=request,
        name="reception/reservations/form.html",
        context={
            "user": _safe_user(current_user),
            "form_data": form_data,
            "form_title": "Nova reserva",
            "form_description": "Registre uma hospedagem futura para um hóspede existente.",
            "submit_label": "Criar reserva",
        },
    )


@router.get("/{reservation_id}/edit", response_class=HTMLResponse)
def edit_reservation_page(
    reservation_id: int,
    request: Request,
    current_user: ReceptionUser,
    service: Reservations,
) -> HTMLResponse:
    try:
        form_data = service.get_form_data(reservation_id)
    except (ReservationNotFoundError, ReservationStateError) as error:
        _raise_http_error(error)

    return templates.TemplateResponse(
        request=request,
        name="reception/reservations/form.html",
        context={
            "user": _safe_user(current_user),
            "form_data": form_data,
            "form_title": "Editar reserva",
            "form_description": "Atualize os dados permitidos da reserva confirmada.",
            "submit_label": "Salvar alterações",
        },
    )


@router.post("", response_model=ReservationView, status_code=status.HTTP_201_CREATED)
def create_reservation(
    payload: ReservationWriteRequest,
    _: ReceptionUser,
    service: Reservations,
) -> ReservationView:
    try:
        return service.create(payload)
    except (
        GuestNotFoundError,
        RoomNotFoundError,
        ReservationConflictError,
        ReservationValidationError,
    ) as error:
        _raise_http_error(error)


@router.put("/{reservation_id}", response_model=ReservationView)
def update_reservation(
    reservation_id: int,
    payload: ReservationWriteRequest,
    _: ReceptionUser,
    service: Reservations,
) -> ReservationView:
    try:
        return service.update(reservation_id, payload)
    except (
        GuestNotFoundError,
        RoomNotFoundError,
        ReservationConflictError,
        ReservationNotFoundError,
        ReservationStateError,
        ReservationValidationError,
    ) as error:
        _raise_http_error(error)


@router.post("/{reservation_id}/cancel", response_model=ReservationView)
def cancel_reservation(
    reservation_id: int,
    _: ReceptionUser,
    service: Reservations,
) -> ReservationView:
    try:
        return service.cancel(reservation_id)
    except (ReservationNotFoundError, ReservationStateError) as error:
        _raise_http_error(error)
