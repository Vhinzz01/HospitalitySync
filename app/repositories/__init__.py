"""Database repositories."""

from app.repositories.guest_repository import GuestRepository
from app.repositories.food_repository import (
    FoodOrderItemRecord,
    FoodOrderRecord,
    FoodRepository,
)
from app.repositories.device_repository import (
    DeviceRecord,
    DeviceRepository,
    DeviceStayRecord,
)
from app.repositories.reception_dashboard_repository import (
    ReceptionDashboardRepository,
)
from app.repositories.reservation_repository import (
    ReservationRecord,
    ReservationRepository,
)
from app.repositories.stay_repository import StayRecord, StayRepository
from app.repositories.service_request_repository import (
    ServiceRequestRecord,
    ServiceRequestRepository,
)
from app.repositories.user_repository import UserRepository

__all__ = [
    "ReceptionDashboardRepository",
    "GuestRepository",
    "FoodOrderItemRecord",
    "FoodOrderRecord",
    "FoodRepository",
    "DeviceRecord",
    "DeviceRepository",
    "DeviceStayRecord",
    "ReservationRecord",
    "ReservationRepository",
    "StayRecord",
    "StayRepository",
    "ServiceRequestRecord",
    "ServiceRequestRepository",
    "UserRepository",
]
