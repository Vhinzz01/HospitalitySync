from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError

from app.core.security import PasswordHasher, hash_device_credential, password_hasher
from app.models import RoomDevice
from app.repositories import DeviceRecord, DeviceRepository
from app.schemas import (
    DeviceRoomOption,
    GuestStayView,
    RoomDeviceCreateRequest,
    RoomDeviceProvisioningView,
    RoomDeviceView,
)


class DeviceError(Exception):
    pass


class DeviceNotFoundError(DeviceError):
    pass


class DeviceConflictError(DeviceError):
    pass


class DeviceAuthenticationError(DeviceError):
    pass


class DeviceService:
    def __init__(
        self,
        repository: DeviceRepository,
        hasher: PasswordHasher = password_hasher,
    ) -> None:
        self._repository = repository
        self._hasher = hasher

    def list_devices(self) -> list[RoomDeviceView]:
        return [self._to_view(record) for record in self._repository.list()]

    def list_room_options(self) -> list[DeviceRoomOption]:
        return [
            DeviceRoomOption(id=room.id, number=room.number)
            for room in self._repository.list_active_rooms()
        ]

    def create_pairing(
        self,
        data: RoomDeviceCreateRequest,
        now: datetime | None = None,
    ) -> RoomDeviceProvisioningView:
        current_time = now or datetime.now(timezone.utc)
        room = self._repository.get_room(data.room_id)
        if room is None or not room.active:
            raise DeviceNotFoundError("Quarto não encontrado ou inativo.")
        if self._repository.get_by_code(data.code) is not None:
            raise DeviceConflictError("Já existe um dispositivo com este código.")
        if self._repository.room_has_active_device(data.room_id):
            raise DeviceConflictError("O quarto já possui um dispositivo ativo.")

        pairing_code = secrets.token_hex(6).upper()
        expires_at = current_time + timedelta(minutes=10)
        device = RoomDevice(
            room_id=data.room_id,
            code=data.code,
            active=False,
            pairing_code_hash=self._hasher.hash(pairing_code),
            pairing_expires_at=expires_at,
        )
        self._repository.add(device)
        self._commit_with_conflict_handling()
        record = self._repository.get_record(device.id)
        if record is None:
            raise DeviceNotFoundError("Dispositivo não encontrado após a criação.")
        return RoomDeviceProvisioningView(
            **self._to_view(record).model_dump(),
            pairing_code=pairing_code,
            pairing_expires_at=expires_at,
        )

    def pair(
        self,
        code: str,
        pairing_code: str,
        now: datetime | None = None,
    ) -> tuple[str, RoomDeviceView]:
        current_time = now or datetime.now(timezone.utc)
        device = self._repository.get_by_code(code)
        if device is None:
            self._hasher.verify_dummy(pairing_code)
            raise DeviceAuthenticationError("Código de pareamento inválido ou expirado.")
        expires_at = device.pairing_expires_at
        if expires_at is not None and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if (
            device.active
            or not device.pairing_code_hash
            or expires_at is None
            or current_time >= expires_at
            or not self._hasher.verify(pairing_code, device.pairing_code_hash)
        ):
            raise DeviceAuthenticationError("Código de pareamento inválido ou expirado.")
        if self._repository.room_has_active_device(device.room_id):
            raise DeviceConflictError("O quarto já possui um dispositivo ativo.")

        credential = secrets.token_urlsafe(48)
        device.credential_hash = hash_device_credential(credential)
        device.active = True
        device.provisioned_at = current_time
        device.last_seen_at = current_time
        device.pairing_code_hash = None
        device.pairing_expires_at = None
        self._commit_with_conflict_handling()
        record = self._repository.get_record(device.id)
        if record is None:
            raise DeviceNotFoundError("Dispositivo não encontrado após o pareamento.")
        return credential, self._to_view(record)

    def authenticate(
        self,
        credential: str | None,
        now: datetime | None = None,
    ) -> RoomDevice:
        if not credential:
            raise DeviceAuthenticationError("Dispositivo não autenticado.")
        device = self._repository.get_active_by_credential_hash(
            hash_device_credential(credential)
        )
        if device is None:
            raise DeviceAuthenticationError("Dispositivo não autenticado.")
        device.last_seen_at = now or datetime.now(timezone.utc)
        self._repository.commit()
        return device

    def get_guest_stay(self, device: RoomDevice) -> GuestStayView:
        context = self._repository.get_stay_context(device)
        if context is None:
            raise DeviceNotFoundError("Quarto associado não encontrado.")
        reservation = context.reservation
        return GuestStayView(
            room_number=context.room.number,
            room_category=context.room.category,
            has_active_stay=reservation is not None,
            guest_name=context.guest_name,
            check_in_date=reservation.check_in_date if reservation else None,
            check_out_date=reservation.check_out_date if reservation else None,
        )

    def revoke(self, device_id: int) -> RoomDeviceView:
        device = self._repository.get(device_id)
        if device is None:
            raise DeviceNotFoundError("Dispositivo não encontrado.")
        device.active = False
        self._repository.commit()
        record = self._repository.get_record(device_id)
        if record is None:
            raise DeviceNotFoundError("Dispositivo não encontrado.")
        return self._to_view(record)

    def _commit_with_conflict_handling(self) -> None:
        try:
            self._repository.commit()
        except IntegrityError as error:
            self._repository.rollback()
            if getattr(error.orig, "sqlstate", None) == "23505":
                raise DeviceConflictError(
                    "O código ou vínculo do dispositivo já está em uso."
                ) from error
            raise

    @staticmethod
    def _to_view(record: DeviceRecord) -> RoomDeviceView:
        device = record.device
        return RoomDeviceView(
            id=device.id,
            code=device.code,
            room_number=record.room_number,
            active=device.active,
            provisioned_at=device.provisioned_at,
            last_seen_at=device.last_seen_at,
        )
