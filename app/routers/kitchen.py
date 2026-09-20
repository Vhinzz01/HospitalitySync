from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.routers.dependencies import FoodOperations, KitchenUser
from app.schemas import (
    FoodOrderStatusUpdate,
    FoodOrderView,
    KitchenUserResponse,
    MenuItemAvailability,
    MenuItemView,
    MenuItemWrite,
)
from app.services import (
    FoodOrderNotFoundError,
    FoodOrderStateError,
    FoodOrderValidationError,
    MenuItemNotFoundError,
)
from app.realtime import realtime_hub


TEMPLATES_DIRECTORY = Path(__file__).resolve().parents[1] / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIRECTORY))
router = APIRouter(prefix="/kitchen", tags=["kitchen"])


def _raise_food_error(error: Exception) -> None:
    if isinstance(error, (MenuItemNotFoundError, FoodOrderNotFoundError)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    if isinstance(error, FoodOrderValidationError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))
    if isinstance(error, FoodOrderStateError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    raise error


@router.get("/login", response_class=HTMLResponse)
def kitchen_login_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request=request, name="kitchen/login.html", context={})


@router.get("", response_class=HTMLResponse)
def kitchen_dashboard(
    request: Request,
    current_user: KitchenUser,
    service: FoodOperations,
    order_status: str | None = Query(default=None, alias="status"),
) -> HTMLResponse:
    try:
        orders = service.list_kitchen_orders(order_status)
    except FoodOrderValidationError as error:
        _raise_food_error(error)
    return templates.TemplateResponse(
        request=request,
        name="kitchen/dashboard.html",
        context={
            "user": KitchenUserResponse.model_validate(current_user),
            "orders": orders,
            "menu": service.list_menu(),
            "status_filter": order_status or "",
        },
    )


@router.post("/menu-items", response_model=MenuItemView, status_code=status.HTTP_201_CREATED)
def create_menu_item(payload: MenuItemWrite, _: KitchenUser, service: FoodOperations) -> MenuItemView:
    try:
        return service.create_menu_item(payload)
    except FoodOrderValidationError as error:
        _raise_food_error(error)


@router.put("/menu-items/{item_id}", response_model=MenuItemView)
def update_menu_item(item_id: int, payload: MenuItemWrite, _: KitchenUser, service: FoodOperations) -> MenuItemView:
    try:
        return service.update_menu_item(item_id, payload)
    except (MenuItemNotFoundError, FoodOrderValidationError) as error:
        _raise_food_error(error)


@router.post("/menu-items/{item_id}/availability", response_model=MenuItemView)
def update_menu_availability(item_id: int, payload: MenuItemAvailability, _: KitchenUser, service: FoodOperations) -> MenuItemView:
    try:
        return service.set_menu_item_availability(item_id, payload)
    except MenuItemNotFoundError as error:
        _raise_food_error(error)


@router.post("/orders/{order_id}/status", response_model=FoodOrderView)
def update_order_status(order_id: int, payload: FoodOrderStatusUpdate, _: KitchenUser, service: FoodOperations, background_tasks: BackgroundTasks) -> FoodOrderView:
    try:
        result = service.update_order_status(order_id, payload)
        room_id = service.get_order_room_id(order_id)
        if room_id is not None:
            background_tasks.add_task(
                realtime_hub.notify_guest,
                room_id,
                {"type": "food_order.updated", "id": result.id, "status": result.status},
            )
        return result
    except (FoodOrderNotFoundError, FoodOrderStateError) as error:
        _raise_food_error(error)
