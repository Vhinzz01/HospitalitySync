from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.routers.dependencies import Devices, ReceptionUser
from app.schemas import (
    ReceptionUserResponse,
    RoomDeviceCreateRequest,
    RoomDeviceProvisioningView,
    RoomDeviceView,
)
from app.services import DeviceConflictError, DeviceNotFoundError


TEMPLATES_DIRECTORY = Path(__file__).resolve().parents[1] / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIRECTORY))
router = APIRouter(prefix="/reception/room-devices", tags=["reception-devices"])


def _raise_http_error(error: Exception) -> None:
    if isinstance(error, DeviceNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    if isinstance(error, DeviceConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    raise error


@router.get("", response_class=HTMLResponse)
def devices_page(
    request: Request,
    current_user: ReceptionUser,
    service: Devices,
) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="reception/devices/list.html",
        context={
            "user": ReceptionUserResponse.model_validate(current_user),
            "devices": service.list_devices(),
            "rooms": service.list_room_options(),
        },
    )


@router.post(
    "",
    response_model=RoomDeviceProvisioningView,
    status_code=status.HTTP_201_CREATED,
)
def create_device_pairing(
    payload: RoomDeviceCreateRequest,
    _: ReceptionUser,
    service: Devices,
) -> RoomDeviceProvisioningView:
    try:
        return service.create_pairing(payload)
    except (DeviceNotFoundError, DeviceConflictError) as error:
        _raise_http_error(error)


@router.post("/{device_id}/revoke", response_model=RoomDeviceView)
def revoke_device(
    device_id: int,
    _: ReceptionUser,
    service: Devices,
) -> RoomDeviceView:
    try:
        return service.revoke(device_id)
    except DeviceNotFoundError as error:
        _raise_http_error(error)
