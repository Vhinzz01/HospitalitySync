"""Pydantic request and response schemas."""

from app.schemas.auth import KitchenUserResponse, LoginRequest, ReceptionUserResponse
from app.schemas.device import (
    DeviceRoomOption,
    GuestStayView,
    RoomDeviceCreateRequest,
    RoomDevicePairRequest,
    RoomDeviceProvisioningView,
    RoomDeviceView,
)
from app.schemas.guest import GuestView, GuestWriteRequest
from app.schemas.food import (
    FoodOrderCreate,
    FoodOrderItemView,
    FoodOrderStatusUpdate,
    FoodOrderView,
    MenuItemAvailability,
    MenuItemView,
    MenuItemWrite,
)
from app.schemas.reception import (
    DashboardRoom,
    DashboardSummary,
    ReceptionDashboard,
    RecentReservation,
)
from app.schemas.reservation import (
    ReservationFormData,
    ReservationGuestOption,
    ReservationRoomOption,
    ReservationView,
    ReservationWriteRequest,
)
from app.schemas.stay import StayOperationView
from app.schemas.service_request import (
    ServiceRequestCreate,
    ServiceRequestStatusUpdate,
    ServiceRequestView,
)

__all__ = [
    "DashboardRoom",
    "DashboardSummary",
    "DeviceRoomOption",
    "GuestView",
    "GuestStayView",
    "GuestWriteRequest",
    "FoodOrderCreate",
    "FoodOrderItemView",
    "FoodOrderStatusUpdate",
    "FoodOrderView",
    "LoginRequest",
    "MenuItemAvailability",
    "MenuItemView",
    "MenuItemWrite",
    "KitchenUserResponse",
    "ReceptionDashboard",
    "ReceptionUserResponse",
    "RecentReservation",
    "ReservationFormData",
    "ReservationGuestOption",
    "ReservationRoomOption",
    "ReservationView",
    "ReservationWriteRequest",
    "RoomDeviceCreateRequest",
    "RoomDevicePairRequest",
    "RoomDeviceProvisioningView",
    "RoomDeviceView",
    "StayOperationView",
    "ServiceRequestCreate",
    "ServiceRequestStatusUpdate",
    "ServiceRequestView",
]
