from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import FoodOrder, Guest, Reservation, Room, ServiceRequest


ACTIVE_RESERVATION_STATUSES = ("CONFIRMED", "CHECKED_IN")


class ReceptionDashboardRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def count_active_rooms_by_status(self, status: str) -> int:
        statement = select(func.count(Room.id)).where(
            Room.active.is_(True),
            Room.status == status,
        )
        return self._session.scalar(statement) or 0

    def count_reservations_for_date(self, target_date: date) -> int:
        statement = select(func.count(Reservation.id)).where(
            Reservation.status.in_(ACTIVE_RESERVATION_STATUSES),
            Reservation.check_in_date <= target_date,
            Reservation.check_out_date >= target_date,
        )
        return self._session.scalar(statement) or 0

    def count_expected_check_ins(self, target_date: date) -> int:
        statement = select(func.count(Reservation.id)).where(
            Reservation.status == "CONFIRMED",
            Reservation.check_in_date == target_date,
        )
        return self._session.scalar(statement) or 0

    def count_expected_check_outs(self, target_date: date) -> int:
        statement = select(func.count(Reservation.id)).where(
            Reservation.status == "CHECKED_IN",
            Reservation.check_out_date == target_date,
        )
        return self._session.scalar(statement) or 0

    def count_active_service_requests(self, category: str) -> int:
        statement = select(func.count(ServiceRequest.id)).where(
            ServiceRequest.category == category,
            ServiceRequest.status.in_(("OPEN", "IN_PROGRESS")),
        )
        return self._session.scalar(statement) or 0

    def count_active_food_orders(self) -> int:
        statement = select(func.count(FoodOrder.id)).where(
            FoodOrder.status.in_(("RECEIVED", "PREPARING", "READY"))
        )
        return self._session.scalar(statement) or 0

    def list_active_rooms(self) -> list[Room]:
        statement = select(Room).where(Room.active.is_(True)).order_by(Room.number)
        return list(self._session.scalars(statement))

    def list_recent_reservations(
        self,
        limit: int = 8,
    ) -> list[tuple[Reservation, str, str]]:
        statement = (
            select(Reservation, Guest.full_name, Room.number)
            .join(Guest, Reservation.guest_id == Guest.id)
            .join(Room, Reservation.room_id == Room.id)
            .order_by(Reservation.created_at.desc(), Reservation.id.desc())
            .limit(limit)
        )
        return [
            (reservation, guest_name, room_number)
            for reservation, guest_name, room_number in self._session.execute(statement)
        ]
