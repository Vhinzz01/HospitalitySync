from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.routers.dependencies import Devices, FoodOperations, RoomDeviceContext, ServiceRequests
from app.schemas import (
    FoodOrderCreate,
    FoodOrderView,
    MenuItemView,
    RoomDevicePairRequest,
    RoomDeviceView,
    ServiceRequestCreate,
    ServiceRequestView,
)
from app.services import (
    ActiveStayRequiredError,
    DeviceAuthenticationError,
    DeviceConflictError,
    DeviceNotFoundError,
    FoodOrderStateError,
    FoodOrderValidationError,
    MenuItemNotFoundError,
)
from app.realtime import realtime_hub


TEMPLATES_DIRECTORY = Path(__file__).resolve().parents[1] / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIRECTORY))
router = APIRouter(prefix="/guest", tags=["guest-device"])
DEVICE_COOKIE = "hospitalitysync_device"


@router.get("/setup", response_class=HTMLResponse)
def setup_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="guest/setup.html",
        context={},
    )


@router.post("/pair", response_model=RoomDeviceView)
def pair_device(
    payload: RoomDevicePairRequest,
    request: Request,
    response: Response,
    service: Devices,
) -> RoomDeviceView:
    try:
        credential, device = service.pair(payload.code, payload.pairing_code)
    except DeviceAuthenticationError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(error),
        ) from error
    except DeviceConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error

    settings = request.app.state.settings
    response.set_cookie(
        DEVICE_COOKIE,
        credential,
        max_age=settings.device_cookie_max_age_seconds,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="strict",
        path="/guest",
    )
    return device


@router.get("", response_class=HTMLResponse)
def guest_dashboard(
    request: Request,
    device: RoomDeviceContext,
    service: Devices,
    request_service: ServiceRequests,
) -> HTMLResponse:
    try:
        stay = service.get_guest_stay(device)
    except DeviceNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    return templates.TemplateResponse(
        request=request,
        name="guest/dashboard.html",
        context={
            "device": device,
            "stay": stay,
            "service_requests": request_service.list_for_device(device),
        },
    )


@router.get("/service-requests", response_model=list[ServiceRequestView])
def list_guest_service_requests(
    device: RoomDeviceContext,
    service: ServiceRequests,
) -> list[ServiceRequestView]:
    return service.list_for_device(device)


@router.post(
    "/service-requests",
    response_model=ServiceRequestView,
    status_code=status.HTTP_201_CREATED,
)
def create_guest_service_request(
    payload: ServiceRequestCreate,
    device: RoomDeviceContext,
    service: ServiceRequests,
    background_tasks: BackgroundTasks,
) -> ServiceRequestView:
    try:
        result = service.create_for_device(device, payload)
        background_tasks.add_task(
            realtime_hub.notify_reception,
            {"type": "service_request.created", "id": result.id},
        )
        return result
    except ActiveStayRequiredError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error


@router.get("/food", response_class=HTMLResponse)
def guest_food_page(
    request: Request,
    device: RoomDeviceContext,
    service: FoodOperations,
) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="guest/food.html",
        context={
            "device": device,
            "menu": service.list_menu(available_only=True),
            "orders": service.list_device_orders(device),
        },
    )


@router.get("/menu", response_model=list[MenuItemView])
def guest_menu(
    _: RoomDeviceContext,
    service: FoodOperations,
) -> list[MenuItemView]:
    return service.list_menu(available_only=True)


@router.get("/orders", response_model=list[FoodOrderView])
def guest_orders(
    device: RoomDeviceContext,
    service: FoodOperations,
) -> list[FoodOrderView]:
    return service.list_device_orders(device)


@router.post("/orders", response_model=FoodOrderView, status_code=status.HTTP_201_CREATED)
def create_guest_order(
    payload: FoodOrderCreate,
    device: RoomDeviceContext,
    service: FoodOperations,
    background_tasks: BackgroundTasks,
) -> FoodOrderView:
    try:
        result = service.create_order(device, payload)
        background_tasks.add_task(
            realtime_hub.notify_kitchen,
            {"type": "food_order.created", "id": result.id},
        )
        return result
    except MenuItemNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except FoodOrderValidationError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    except FoodOrderStateError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
