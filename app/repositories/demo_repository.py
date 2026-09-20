from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Guest, MenuItem, Reservation, Room, RoomDevice, User


class DemoRepository:
    """Persistence used only by the explicitly enabled local demonstration mode."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def user_by_email(self, email: str) -> User | None:
        return self._session.scalar(select(User).where(User.email == email))

    def room_by_number(self, number: str) -> Room | None:
        return self._session.scalar(select(Room).where(Room.number == number))

    def guest_by_document(self, document: str) -> Guest | None:
        return self._session.scalar(select(Guest).where(Guest.document == document))

    def reservation_for_room(self, room_id: int) -> Reservation | None:
        return self._session.scalar(
            select(Reservation)
            .where(Reservation.room_id == room_id)
            .order_by(Reservation.id.desc())
        )

    def device_by_code(self, code: str) -> RoomDevice | None:
        return self._session.scalar(select(RoomDevice).where(RoomDevice.code == code))

    def menu_item_by_name(self, name: str) -> MenuItem | None:
        return self._session.scalar(select(MenuItem).where(MenuItem.name == name))

    def add(self, entity: object) -> None:
        self._session.add(entity)

    def flush(self) -> None:
        self._session.flush()

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()
