from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database.connection import get_database_session
from app.models import RoomDevice, User
from app.repositories import (
    GuestRepository,
    FoodRepository,
    DeviceRepository,
    ReceptionDashboardRepository,
    ReservationRepository,
    StayRepository,
    ServiceRequestRepository,
    UserRepository,
    DemoRepository,
)
from app.services import (
    AuthenticationService,
    ReceptionDashboardService,
    ReservationService,
    GuestService,
    FoodService,
    DeviceAuthenticationError,
    DeviceService,
    StayService,
    ServiceRequestService,
    DemoAccessService,
)


DatabaseSession = Annotated[Session, Depends(get_database_session)]


def get_authentication_service(session: DatabaseSession) -> AuthenticationService:
    return AuthenticationService(UserRepository(session))


Authentication = Annotated[
    AuthenticationService,
    Depends(get_authentication_service),
]


def get_demo_access_service(session: DatabaseSession) -> DemoAccessService:
    return DemoAccessService(DemoRepository(session))


DemoAccessOperations = Annotated[
    DemoAccessService,
    Depends(get_demo_access_service),
]


def require_reception_user(
    request: Request,
    authentication: Authentication,
) -> User:
    user_id = request.session.get("user_id")
    if not isinstance(user_id, int):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    user = authentication.get_authenticated_receptionist(user_id)
    if user is None:
        request.session.clear()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    return user


ReceptionUser = Annotated[User, Depends(require_reception_user)]


def require_kitchen_user(
    request: Request,
    authentication: Authentication,
) -> User:
    user_id = request.session.get("user_id")
    if not isinstance(user_id, int):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )
    user = authentication.get_authenticated_kitchen_user(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Kitchen role required.",
        )
    return user


KitchenUser = Annotated[User, Depends(require_kitchen_user)]


def get_reception_dashboard_service(
    session: DatabaseSession,
) -> ReceptionDashboardService:
    return ReceptionDashboardService(ReceptionDashboardRepository(session))


ReceptionDashboard = Annotated[
    ReceptionDashboardService,
    Depends(get_reception_dashboard_service),
]


def get_reservation_service(session: DatabaseSession) -> ReservationService:
    return ReservationService(ReservationRepository(session))


Reservations = Annotated[ReservationService, Depends(get_reservation_service)]


def get_guest_service(session: DatabaseSession) -> GuestService:
    return GuestService(GuestRepository(session))


Guests = Annotated[GuestService, Depends(get_guest_service)]


def get_stay_service(session: DatabaseSession) -> StayService:
    return StayService(StayRepository(session))


Stays = Annotated[StayService, Depends(get_stay_service)]


def get_device_service(session: DatabaseSession) -> DeviceService:
    return DeviceService(DeviceRepository(session))


Devices = Annotated[DeviceService, Depends(get_device_service)]


def require_room_device(request: Request, service: Devices):
    credential = request.cookies.get("hospitalitysync_device")
    try:
        return service.authenticate(credential)
    except DeviceAuthenticationError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(error),
        ) from error


RoomDeviceContext = Annotated[RoomDevice, Depends(require_room_device)]


def get_service_request_service(session: DatabaseSession) -> ServiceRequestService:
    return ServiceRequestService(ServiceRequestRepository(session))


ServiceRequests = Annotated[
    ServiceRequestService,
    Depends(get_service_request_service),
]


def get_food_service(session: DatabaseSession) -> FoodService:
    return FoodService(FoodRepository(session))


FoodOperations = Annotated[FoodService, Depends(get_food_service)]
