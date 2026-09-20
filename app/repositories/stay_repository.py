from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Guest, Reservation, Room


@dataclass(frozen=True, slots=True)
class StayRecord:
    reservation: Reservation
    guest_name: str
    room_number: str


class StayRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_by_status(self, status: str) -> list[StayRecord]:
        statement = (
            select(Reservation, Guest.full_name, Room.number)
            .join(Guest, Reservation.guest_id == Guest.id)
            .join(Room, Reservation.room_id == Room.id)
            .where(Reservation.status == status)
            .order_by(Reservation.check_in_date, Room.number, Reservation.id)
        )
        return [
            StayRecord(reservation, guest_name, room_number)
            for reservation, guest_name, room_number in self._session.execute(statement)
        ]

    def get_reservation_for_update(self, reservation_id: int) -> Reservation | None:
        statement = (
            select(Reservation)
            .where(Reservation.id == reservation_id)
            .with_for_update()
        )
        return self._session.scalar(statement)

    def get_room_for_update(self, room_id: int) -> Room | None:
        statement = select(Room).where(Room.id == room_id).with_for_update()
        return self._session.scalar(statement)

    def room_has_active_stay(
        self,
        room_id: int,
        exclude_reservation_id: int | None = None,
    ) -> bool:
        statement = select(Reservation.id).where(
            Reservation.room_id == room_id,
            Reservation.status == "CHECKED_IN",
        )
        if exclude_reservation_id is not None:
            statement = statement.where(Reservation.id != exclude_reservation_id)
        return self._session.scalar(statement.limit(1)) is not None

    def get_record(self, reservation_id: int) -> StayRecord | None:
        statement = (
            select(Reservation, Guest.full_name, Room.number)
            .join(Guest, Reservation.guest_id == Guest.id)
            .join(Room, Reservation.room_id == Room.id)
            .where(Reservation.id == reservation_id)
        )
        row = self._session.execute(statement).one_or_none()
        if row is None:
            return None
        reservation, guest_name, room_number = row
        return StayRecord(reservation, guest_name, room_number)

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()
