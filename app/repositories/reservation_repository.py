from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import Select, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Guest, Reservation, Room


ACTIVE_RESERVATION_STATUSES = ("CONFIRMED", "CHECKED_IN")
POSTGRESQL_EXCLUSION_VIOLATION = "23P01"


@dataclass(frozen=True, slots=True)
class ReservationRecord:
    reservation: Reservation
    guest_name: str
    room_number: str


class ReservationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list(
        self,
        status: str | None = None,
        period_start: date | None = None,
        period_end: date | None = None,
    ) -> list[ReservationRecord]:
        statement = self._base_record_statement()
        if status is not None:
            statement = statement.where(Reservation.status == status)
        if period_start is not None:
            statement = statement.where(Reservation.check_out_date >= period_start)
        if period_end is not None:
            statement = statement.where(Reservation.check_in_date <= period_end)

        statement = statement.order_by(
            Reservation.check_in_date.desc(),
            Reservation.id.desc(),
        )
        return self._records(statement)

    def get_record(self, reservation_id: int) -> ReservationRecord | None:
        statement = self._base_record_statement().where(
            Reservation.id == reservation_id
        )
        row = self._session.execute(statement).one_or_none()
        if row is None:
            return None
        reservation, guest_name, room_number = row
        return ReservationRecord(reservation, guest_name, room_number)

    def get(self, reservation_id: int) -> Reservation | None:
        return self._session.get(Reservation, reservation_id)

    def get_guest(self, guest_id: int) -> Guest | None:
        return self._session.get(Guest, guest_id)

    def get_room(self, room_id: int) -> Room | None:
        return self._session.get(Room, room_id)

    def list_active_guests(self) -> list[Guest]:
        statement = (
            select(Guest)
            .where(Guest.active.is_(True))
            .order_by(Guest.full_name, Guest.id)
        )
        return list(self._session.scalars(statement))

    def list_active_rooms(self) -> list[Room]:
        statement = (
            select(Room).where(Room.active.is_(True)).order_by(Room.number, Room.id)
        )
        return list(self._session.scalars(statement))

    def has_overlapping_reservation(
        self,
        room_id: int,
        check_in_date: date,
        check_out_date: date,
        exclude_reservation_id: int | None = None,
    ) -> bool:
        statement = select(Reservation.id).where(
            Reservation.room_id == room_id,
            Reservation.status.in_(ACTIVE_RESERVATION_STATUSES),
            Reservation.check_in_date < check_out_date,
            Reservation.check_out_date > check_in_date,
        )
        if exclude_reservation_id is not None:
            statement = statement.where(Reservation.id != exclude_reservation_id)
        return self._session.scalar(statement.limit(1)) is not None

    def add(self, reservation: Reservation) -> None:
        self._session.add(reservation)

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()

    @staticmethod
    def is_exclusion_violation(error: IntegrityError) -> bool:
        return getattr(error.orig, "sqlstate", None) == POSTGRESQL_EXCLUSION_VIOLATION

    @staticmethod
    def _base_record_statement() -> Select[tuple[Reservation, str, str]]:
        return (
            select(Reservation, Guest.full_name, Room.number)
            .join(Guest, Reservation.guest_id == Guest.id)
            .join(Room, Reservation.room_id == Room.id)
        )

    def _records(
        self,
        statement: Select[tuple[Reservation, str, str]],
    ) -> list[ReservationRecord]:
        return [
            ReservationRecord(reservation, guest_name, room_number)
            for reservation, guest_name, room_number in self._session.execute(statement)
        ]
