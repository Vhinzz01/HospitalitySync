from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.routers.dependencies import Guests, ReceptionUser
from app.schemas import GuestView, GuestWriteRequest, ReceptionUserResponse
from app.services import (
    GuestConflictError,
    GuestManagementNotFoundError,
    GuestValidationError,
)


TEMPLATES_DIRECTORY = Path(__file__).resolve().parents[1] / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIRECTORY))
router = APIRouter(prefix="/reception/guests", tags=["reception-guests"])


def _raise_http_error(error: Exception) -> None:
    if isinstance(error, GuestManagementNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    if isinstance(error, GuestConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    if isinstance(error, GuestValidationError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))
    raise error


@router.get("", response_class=HTMLResponse)
def guests_page(
    request: Request,
    current_user: ReceptionUser,
    service: Guests,
    state: str = Query(default="active"),
    search: str | None = Query(default=None, max_length=150),
) -> HTMLResponse:
    try:
        guests = service.list_guests(state=state, search=search)
    except GuestValidationError as error:
        _raise_http_error(error)
    return templates.TemplateResponse(
        request=request,
        name="reception/guests/list.html",
        context={
            "user": ReceptionUserResponse.model_validate(current_user),
            "guests": guests,
            "filters": {"state": state, "search": search or ""},
        },
    )


@router.get("/new", response_class=HTMLResponse)
def new_guest_page(request: Request, current_user: ReceptionUser) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="reception/guests/form.html",
        context={
            "user": ReceptionUserResponse.model_validate(current_user),
            "guest": None,
            "form_title": "Novo hóspede",
            "submit_label": "Cadastrar hóspede",
        },
    )


@router.get("/{guest_id}/edit", response_class=HTMLResponse)
def edit_guest_page(
    guest_id: int,
    request: Request,
    current_user: ReceptionUser,
    service: Guests,
) -> HTMLResponse:
    try:
        guest = service.get(guest_id)
    except GuestManagementNotFoundError as error:
        _raise_http_error(error)
    return templates.TemplateResponse(
        request=request,
        name="reception/guests/form.html",
        context={
            "user": ReceptionUserResponse.model_validate(current_user),
            "guest": guest,
            "form_title": "Editar hóspede",
            "submit_label": "Salvar alterações",
        },
    )


@router.post("", response_model=GuestView, status_code=status.HTTP_201_CREATED)
def create_guest(
    payload: GuestWriteRequest,
    _: ReceptionUser,
    service: Guests,
) -> GuestView:
    try:
        return service.create(payload)
    except (GuestConflictError, GuestValidationError) as error:
        _raise_http_error(error)


@router.put("/{guest_id}", response_model=GuestView)
def update_guest(
    guest_id: int,
    payload: GuestWriteRequest,
    _: ReceptionUser,
    service: Guests,
) -> GuestView:
    try:
        return service.update(guest_id, payload)
    except (
        GuestManagementNotFoundError,
        GuestConflictError,
        GuestValidationError,
    ) as error:
        _raise_http_error(error)


@router.post("/{guest_id}/deactivate", response_model=GuestView)
def deactivate_guest(
    guest_id: int,
    _: ReceptionUser,
    service: Guests,
) -> GuestView:
    try:
        return service.deactivate(guest_id)
    except GuestManagementNotFoundError as error:
        _raise_http_error(error)
