from __future__ import annotations

from datetime import date

from sqlalchemy.exc import IntegrityError

from app.models import Reservation
from app.repositories import ReservationRecord, ReservationRepository
from app.schemas import (
    ReservationFormData,
    ReservationGuestOption,
    ReservationRoomOption,
    ReservationView,
    ReservationWriteRequest,
)


VALID_RESERVATION_STATUSES = {
    "CONFIRMED",
    "CHECKED_IN",
    "CHECKED_OUT",
    "CANCELLED",
}

RESERVATION_STATUS_PRESENTATION = {
    "CONFIRMED": ("Confirmada", "confirmed"),
    "CHECKED_IN": ("Check-in realizado", "checked-in"),
    "CHECKED_OUT": ("Finalizada", "checked-out"),
    "CANCELLED": ("Cancelada", "cancelled"),
}


class ReservationError(Exception):
    pass


class ReservationNotFoundError(ReservationError):
    pass


class GuestNotFoundError(ReservationError):
    pass


class RoomNotFoundError(ReservationError):
    pass


class ReservationConflictError(ReservationError):
    pass


class ReservationValidationError(ReservationError):
    pass


class ReservationStateError(ReservationError):
    pass


class ReservationService:
    def __init__(self, repository: ReservationRepository) -> None:
        self._repository = repository

    def list_reservations(
        self,
        status: str | None = None,
        period_start: date | None = None,
        period_end: date | None = None,
    ) -> list[ReservationView]:
        normalized_status = status or None
        if normalized_status is not None and normalized_status not in (
            VALID_RESERVATION_STATUSES
        ):
            raise ReservationValidationError("Status de reserva inválido.")
        if period_start and period_end and period_end < period_start:
            raise ReservationValidationError(
                "A data final do filtro deve ser igual ou posterior à data inicial."
            )

        return [
            self._to_view(record)
            for record in self._repository.list(
                status=normalized_status,
                period_start=period_start,
                period_end=period_end,
            )
        ]

    def get_form_data(self, reservation_id: int | None = None) -> ReservationFormData:
        reservation = None
        if reservation_id is not None:
            record = self._repository.get_record(reservation_id)
            if record is None:
                raise ReservationNotFoundError("Reserva não encontrada.")
            if record.reservation.status != "CONFIRMED":
                raise ReservationStateError(
                    "Somente reservas confirmadas podem ser editadas."
                )
            reservation = self._to_view(record)

        guests = [
            ReservationGuestOption(id=guest.id, name=guest.full_name)
            for guest in self._repository.list_active_guests()
        ]
        rooms = [
            ReservationRoomOption(
                id=room.id,
                number=room.number,
                category=room.category,
                capacity=room.capacity,
            )
            for room in self._repository.list_active_rooms()
        ]
        return ReservationFormData(
            guests=guests,
            rooms=rooms,
            reservation=reservation,
        )

    def create(self, data: ReservationWriteRequest) -> ReservationView:
        self._validate_write_data(data)
        self._ensure_available(data)

        reservation = Reservation(
            guest_id=data.guest_id,
            room_id=data.room_id,
            check_in_date=data.check_in_date,
            check_out_date=data.check_out_date,
            guest_count=data.guest_count,
            status="CONFIRMED",
        )
        self._repository.add(reservation)
        self._commit_with_conflict_handling()
        record = self._repository.get_record(reservation.id)
        if record is None:
            raise ReservationNotFoundError("Reserva não encontrada após a criação.")
        return self._to_view(record)

    def update(
        self,
        reservation_id: int,
        data: ReservationWriteRequest,
    ) -> ReservationView:
        reservation = self._repository.get(reservation_id)
        if reservation is None:
            raise ReservationNotFoundError("Reserva não encontrada.")
        if reservation.status != "CONFIRMED":
            raise ReservationStateError(
                "Somente reservas confirmadas podem ser editadas."
            )

        self._validate_write_data(data)
        self._ensure_available(data, exclude_reservation_id=reservation_id)

        reservation.guest_id = data.guest_id
        reservation.room_id = data.room_id
        reservation.check_in_date = data.check_in_date
        reservation.check_out_date = data.check_out_date
        reservation.guest_count = data.guest_count
        self._commit_with_conflict_handling()

        record = self._repository.get_record(reservation_id)
        if record is None:
            raise ReservationNotFoundError("Reserva não encontrada após a edição.")
        return self._to_view(record)

    def cancel(self, reservation_id: int) -> ReservationView:
        reservation = self._repository.get(reservation_id)
        if reservation is None:
            raise ReservationNotFoundError("Reserva não encontrada.")
        if reservation.status == "CANCELLED":
            record = self._repository.get_record(reservation_id)
            if record is None:
                raise ReservationNotFoundError("Reserva não encontrada.")
            return self._to_view(record)
        if reservation.status != "CONFIRMED":
            raise ReservationStateError(
                "Somente reservas confirmadas podem ser canceladas."
            )

        reservation.status = "CANCELLED"
        self._repository.commit()
        record = self._repository.get_record(reservation_id)
        if record is None:
            raise ReservationNotFoundError("Reserva não encontrada após o cancelamento.")
        return self._to_view(record)

    def _validate_write_data(self, data: ReservationWriteRequest) -> None:
        if data.check_out_date <= data.check_in_date:
            raise ReservationValidationError(
                "A data de saída deve ser posterior à data de entrada."
            )

        guest = self._repository.get_guest(data.guest_id)
        if guest is None or not guest.active:
            raise GuestNotFoundError("Hóspede não encontrado ou inativo.")

        room = self._repository.get_room(data.room_id)
        if room is None or not room.active:
            raise RoomNotFoundError("Quarto não encontrado ou inativo.")
        if data.guest_count > room.capacity:
            raise ReservationValidationError(
                "A quantidade de hóspedes excede a capacidade do quarto."
            )

    def _ensure_available(
        self,
        data: ReservationWriteRequest,
        exclude_reservation_id: int | None = None,
    ) -> None:
        if self._repository.has_overlapping_reservation(
            room_id=data.room_id,
            check_in_date=data.check_in_date,
            check_out_date=data.check_out_date,
            exclude_reservation_id=exclude_reservation_id,
        ):
            raise ReservationConflictError(
                "O quarto já possui uma reserva ativa nesse período."
            )

    def _commit_with_conflict_handling(self) -> None:
        try:
            self._repository.commit()
        except IntegrityError as error:
            self._repository.rollback()
            if self._repository.is_exclusion_violation(error):
                raise ReservationConflictError(
                    "O quarto já possui uma reserva ativa nesse período."
                ) from error
            raise

    @staticmethod
    def _to_view(record: ReservationRecord) -> ReservationView:
        reservation = record.reservation
        status_label, status_style = RESERVATION_STATUS_PRESENTATION[
            reservation.status
        ]
        return ReservationView(
            id=reservation.id,
            guest_id=reservation.guest_id,
            guest_name=record.guest_name,
            room_id=reservation.room_id,
            room_number=record.room_number,
            check_in_date=reservation.check_in_date,
            check_out_date=reservation.check_out_date,
            guest_count=reservation.guest_count,
            status=reservation.status,
            status_label=status_label,
            status_style=status_style,
            period=(
                f"{reservation.check_in_date:%d/%m/%Y} — "
                f"{reservation.check_out_date:%d/%m/%Y}"
            ),
        )
