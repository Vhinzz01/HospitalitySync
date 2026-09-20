"""Application services."""

from app.services.authentication import AuthenticationService
from app.services.demo_access import DemoAccessError, DemoAccessService
from app.services.devices import (
    DeviceAuthenticationError,
    DeviceConflictError,
    DeviceError,
    DeviceNotFoundError,
    DeviceService,
)
from app.services.guests import (
    GuestConflictError,
    GuestError,
    GuestNotFoundError as GuestManagementNotFoundError,
    GuestService,
    GuestValidationError,
)
from app.services.food import (
    FoodError,
    FoodOrderNotFoundError,
    FoodOrderStateError,
    FoodOrderValidationError,
    FoodService,
    MenuItemNotFoundError,
)
from app.services.reception_dashboard import ReceptionDashboardService
from app.services.reservations import (
    GuestNotFoundError,
    ReservationConflictError,
    ReservationError,
    ReservationNotFoundError,
    ReservationService,
    ReservationStateError,
    ReservationValidationError,
    RoomNotFoundError,
)
from app.services.stays import (
    StayError,
    StayNotFoundError,
    StayService,
    StayStateConflictError,
)
from app.services.service_requests import (
    ActiveStayRequiredError,
    ServiceRequestError,
    ServiceRequestNotFoundError,
    ServiceRequestService,
    ServiceRequestStateError,
)

__all__ = [
    "AuthenticationService",
    "DemoAccessError",
    "DemoAccessService",
    "DeviceAuthenticationError",
    "DeviceConflictError",
    "DeviceError",
    "DeviceNotFoundError",
    "DeviceService",
    "GuestNotFoundError",
    "GuestConflictError",
    "GuestError",
    "GuestManagementNotFoundError",
    "GuestService",
    "GuestValidationError",
    "FoodError",
    "FoodOrderNotFoundError",
    "FoodOrderStateError",
    "FoodOrderValidationError",
    "FoodService",
    "MenuItemNotFoundError",
    "ReceptionDashboardService",
    "ReservationConflictError",
    "ReservationError",
    "ReservationNotFoundError",
    "ReservationService",
    "ReservationStateError",
    "ReservationValidationError",
    "RoomNotFoundError",
    "StayError",
    "StayNotFoundError",
    "StayService",
    "StayStateConflictError",
    "ActiveStayRequiredError",
    "ServiceRequestError",
    "ServiceRequestNotFoundError",
    "ServiceRequestService",
    "ServiceRequestStateError",
]
