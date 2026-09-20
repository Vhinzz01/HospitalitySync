from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Guest, Reservation, Room, ServiceRequest


@dataclass(frozen=True, slots=True)
class ServiceRequestRecord:
    request: ServiceRequest
    room_number: str
    guest_name: str | None


class ServiceRequestRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_all(
        self,
        category: str | None = None,
        request_status: str | None = None,
    ) -> list[ServiceRequestRecord]:
        statement = (
            select(ServiceRequest, Room.number, Guest.full_name)
            .join(Room, ServiceRequest.room_id == Room.id)
            .outerjoin(Reservation, ServiceRequest.reservation_id == Reservation.id)
            .outerjoin(Guest, Reservation.guest_id == Guest.id)
        )
        if category:
            statement = statement.where(ServiceRequest.category == category)
        if request_status:
            statement = statement.where(ServiceRequest.status == request_status)
        statement = statement.order_by(ServiceRequest.created_at.desc())
        return [ServiceRequestRecord(*row) for row in self._session.execute(statement)]

    def list_for_reservation(
        self, room_id: int, reservation_id: int
    ) -> list[ServiceRequestRecord]:
        statement = (
            select(ServiceRequest, Room.number, Guest.full_name)
            .join(Room, ServiceRequest.room_id == Room.id)
            .join(Reservation, ServiceRequest.reservation_id == Reservation.id)
            .join(Guest, Reservation.guest_id == Guest.id)
            .where(
                ServiceRequest.room_id == room_id,
                ServiceRequest.reservation_id == reservation_id,
            )
            .order_by(ServiceRequest.created_at.desc())
        )
        return [ServiceRequestRecord(*row) for row in self._session.execute(statement)]

    def get_for_update(self, request_id: int) -> ServiceRequest | None:
        return self._session.scalar(
            select(ServiceRequest)
            .where(ServiceRequest.id == request_id)
            .with_for_update()
        )

    def get_record(self, request_id: int) -> ServiceRequestRecord | None:
        row = self._session.execute(
            select(ServiceRequest, Room.number, Guest.full_name)
            .join(Room, ServiceRequest.room_id == Room.id)
            .outerjoin(Reservation, ServiceRequest.reservation_id == Reservation.id)
            .outerjoin(Guest, Reservation.guest_id == Guest.id)
            .where(ServiceRequest.id == request_id)
        ).one_or_none()
        return ServiceRequestRecord(*row) if row else None

    def get_room_id(self, request_id: int) -> int | None:
        return self._session.scalar(
            select(ServiceRequest.room_id).where(ServiceRequest.id == request_id)
        )

    def get_active_reservation(self, room_id: int) -> Reservation | None:
        return self._session.scalar(
            select(Reservation).where(
                Reservation.room_id == room_id,
                Reservation.status == "CHECKED_IN",
            )
        )

    def add(self, service_request: ServiceRequest) -> None:
        self._session.add(service_request)

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()
