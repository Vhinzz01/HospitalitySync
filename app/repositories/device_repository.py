from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Guest, Reservation, Room, RoomDevice


@dataclass(frozen=True, slots=True)
class DeviceRecord:
    device: RoomDevice
    room_number: str


@dataclass(frozen=True, slots=True)
class DeviceStayRecord:
    device: RoomDevice
    room: Room
    reservation: Reservation | None
    guest_name: str | None


class DeviceRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list(self) -> list[DeviceRecord]:
        statement = (
            select(RoomDevice, Room.number)
            .join(Room, RoomDevice.room_id == Room.id)
            .order_by(Room.number, RoomDevice.id.desc())
        )
        return [
            DeviceRecord(device, room_number)
            for device, room_number in self._session.execute(statement)
        ]

    def get(self, device_id: int) -> RoomDevice | None:
        return self._session.get(RoomDevice, device_id)

    def get_room(self, room_id: int) -> Room | None:
        return self._session.get(Room, room_id)

    def list_active_rooms(self) -> list[Room]:
        return list(
            self._session.scalars(
                select(Room).where(Room.active.is_(True)).order_by(Room.number)
            )
        )

    def get_by_code(self, code: str) -> RoomDevice | None:
        return self._session.scalar(
            select(RoomDevice).where(RoomDevice.code == code.upper())
        )

    def get_active_by_credential_hash(self, credential_hash: str) -> RoomDevice | None:
        return self._session.scalar(
            select(RoomDevice).where(
                RoomDevice.credential_hash == credential_hash,
                RoomDevice.active.is_(True),
            )
        )

    def room_has_active_device(self, room_id: int) -> bool:
        return self._session.scalar(
            select(RoomDevice.id)
            .where(RoomDevice.room_id == room_id, RoomDevice.active.is_(True))
            .limit(1)
        ) is not None

    def get_record(self, device_id: int) -> DeviceRecord | None:
        row = self._session.execute(
            select(RoomDevice, Room.number)
            .join(Room, RoomDevice.room_id == Room.id)
            .where(RoomDevice.id == device_id)
        ).one_or_none()
        if row is None:
            return None
        device, room_number = row
        return DeviceRecord(device, room_number)

    def get_stay_context(self, device: RoomDevice) -> DeviceStayRecord | None:
        room = self._session.get(Room, device.room_id)
        if room is None:
            return None
        row = self._session.execute(
            select(Reservation, Guest.full_name)
            .join(Guest, Reservation.guest_id == Guest.id)
            .where(
                Reservation.room_id == device.room_id,
                Reservation.status == "CHECKED_IN",
            )
            .limit(1)
        ).one_or_none()
        if row is None:
            return DeviceStayRecord(device, room, None, None)
        reservation, guest_name = row
        return DeviceStayRecord(device, room, reservation, guest_name)

    def add(self, device: RoomDevice) -> None:
        self._session.add(device)

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()
