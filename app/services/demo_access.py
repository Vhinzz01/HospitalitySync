from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.exc import IntegrityError

from app.core.security import hash_device_credential, password_hasher
from app.models import Guest, MenuItem, Reservation, Room, RoomDevice, User
from app.repositories.demo_repository import DemoRepository


class DemoAccessError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class DemoAccess:
    destination: str
    user_id: int | None = None
    device_credential: str | None = None


class DemoAccessService:
    RECEPTION_EMAIL = "demo.reception@hospitalitysync.test"
    KITCHEN_EMAIL = "demo.kitchen@hospitalitysync.test"
    ROOM_NUMBER = "DEMO-101"
    DEVICE_CODE = "DEMO-ROOM-101"
    GUEST_DOCUMENT = "HOSPITALITYSYNC-DEMO-GUEST"

    def __init__(self, repository: DemoRepository) -> None:
        self._repository = repository

    def enter(self, area: str) -> DemoAccess:
        try:
            if area == "reception":
                user = self._ensure_user(
                    self.RECEPTION_EMAIL, "Recepção Demonstração", "RECEPTION"
                )
                self._ensure_guest_environment()
                self._repository.commit()
                return DemoAccess(destination="/reception", user_id=user.id)
            if area == "kitchen":
                user = self._ensure_user(
                    self.KITCHEN_EMAIL, "Cozinha Demonstração", "KITCHEN"
                )
                self._ensure_guest_environment()
                self._repository.commit()
                return DemoAccess(destination="/kitchen", user_id=user.id)
            if area == "guest":
                credential = self._ensure_guest_environment()
                self._repository.commit()
                return DemoAccess(
                    destination="/guest", device_credential=credential
                )
        except IntegrityError as error:
            self._repository.rollback()
            raise DemoAccessError(
                "Não foi possível preparar o ambiente de demonstração."
            ) from error
        raise DemoAccessError("Ambiente de demonstração inválido.")

    def _ensure_user(self, email: str, name: str, role: str) -> User:
        user = self._repository.user_by_email(email)
        if user is None:
            user = User(
                name=name,
                email=email,
                password_hash=password_hasher.hash(secrets.token_urlsafe(48)),
                role=role,
                active=True,
            )
            self._repository.add(user)
            self._repository.flush()
        else:
            user.active = True
            user.role = role
        return user

    def _ensure_guest_environment(self) -> str:
        now = datetime.now(timezone.utc)
        today = date.today()
        room = self._repository.room_by_number(self.ROOM_NUMBER)
        if room is None:
            room = Room(
                number=self.ROOM_NUMBER,
                category="Suíte demonstração",
                capacity=2,
                status="OCCUPIED",
                active=True,
            )
            self._repository.add(room)
            self._repository.flush()
        else:
            room.active = True
            room.status = "OCCUPIED"

        guest = self._repository.guest_by_document(self.GUEST_DOCUMENT)
        if guest is None:
            guest = Guest(
                full_name="Hóspede Demonstração",
                document=self.GUEST_DOCUMENT,
                email="demo.guest@hospitalitysync.test",
                active=True,
            )
            self._repository.add(guest)
            self._repository.flush()

        reservation = self._repository.reservation_for_room(room.id)
        if reservation is None:
            reservation = Reservation(
                guest_id=guest.id,
                room_id=room.id,
                check_in_date=today,
                check_out_date=today + timedelta(days=2),
                guest_count=1,
                status="CHECKED_IN",
                actual_check_in_at=now,
                notes="Ambiente temporário de demonstração.",
            )
            self._repository.add(reservation)
        else:
            reservation.guest_id = guest.id
            reservation.check_in_date = today
            reservation.check_out_date = today + timedelta(days=2)
            reservation.guest_count = 1
            reservation.status = "CHECKED_IN"
            reservation.actual_check_in_at = now
            reservation.actual_check_out_at = None

        credential = secrets.token_urlsafe(48)
        device = self._repository.device_by_code(self.DEVICE_CODE)
        if device is None:
            device = RoomDevice(room_id=room.id, code=self.DEVICE_CODE)
            self._repository.add(device)
        device.room_id = room.id
        device.credential_hash = hash_device_credential(credential)
        device.active = True
        device.provisioned_at = now
        device.last_seen_at = now
        device.pairing_code_hash = None
        device.pairing_expires_at = None
        self._ensure_menu()
        return credential

    def _ensure_menu(self) -> None:
        items = (
            ("Sanduíche Hospitality", "Pão artesanal, queijo e salada", "32.00"),
            ("Bowl da estação", "Legumes, folhas e molho da casa", "28.00"),
            ("Suco natural", "Fruta do dia", "12.00"),
        )
        for name, description, price in items:
            item = self._repository.menu_item_by_name(name)
            if item is None:
                self._repository.add(
                    MenuItem(
                        name=name,
                        description=description,
                        price=Decimal(price),
                        available=True,
                    )
                )
            else:
                item.available = True
