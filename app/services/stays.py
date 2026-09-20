from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError

from app.repositories import StayRecord, StayRepository
from app.schemas import StayOperationView


class StayError(Exception):
    pass


class StayNotFoundError(StayError):
    pass


class StayStateConflictError(StayError):
    pass


class StayService:
    def __init__(self, repository: StayRepository) -> None:
        self._repository = repository

    def list_expected_check_ins(self) -> list[StayOperationView]:
        return [
            self._to_view(record)
            for record in self._repository.list_by_status("CONFIRMED")
        ]

    def list_active_stays(self) -> list[StayOperationView]:
        return [
            self._to_view(record)
            for record in self._repository.list_by_status("CHECKED_IN")
        ]

    def check_in(
        self,
        reservation_id: int,
        occurred_at: datetime | None = None,
    ) -> StayOperationView:
        current_time = occurred_at or datetime.now(timezone.utc)
        reservation = self._repository.get_reservation_for_update(reservation_id)
        if reservation is None:
            raise StayNotFoundError("Reserva não encontrada.")
        if reservation.status != "CONFIRMED":
            raise StayStateConflictError(
                "Somente reservas confirmadas podem receber check-in."
            )
        if current_time.date() < reservation.check_in_date:
            raise StayStateConflictError(
                "O check-in não pode ocorrer antes da data prevista."
            )
        if current_time.date() >= reservation.check_out_date:
            raise StayStateConflictError(
                "O período previsto para esta reserva já terminou."
            )

        room = self._repository.get_room_for_update(reservation.room_id)
        if room is None or not room.active:
            raise StayStateConflictError("O quarto da reserva não está ativo.")
        if room.status != "AVAILABLE":
            raise StayStateConflictError("O quarto não está disponível para check-in.")
        if self._repository.room_has_active_stay(room.id, reservation.id):
            raise StayStateConflictError("O quarto já possui uma hospedagem ativa.")

        reservation.status = "CHECKED_IN"
        reservation.actual_check_in_at = current_time
        room.status = "OCCUPIED"
        self._commit()
        return self._get_view(reservation_id)

    def check_out(
        self,
        reservation_id: int,
        occurred_at: datetime | None = None,
    ) -> StayOperationView:
        current_time = occurred_at or datetime.now(timezone.utc)
        reservation = self._repository.get_reservation_for_update(reservation_id)
        if reservation is None:
            raise StayNotFoundError("Hospedagem não encontrada.")
        if reservation.status != "CHECKED_IN":
            raise StayStateConflictError(
                "Somente hospedagens ativas podem receber check-out."
            )
        check_in_time = reservation.actual_check_in_at
        if check_in_time is not None and check_in_time.tzinfo is None:
            check_in_time = check_in_time.replace(tzinfo=timezone.utc)
        if check_in_time is not None and current_time <= check_in_time:
            raise StayStateConflictError(
                "O check-out deve ocorrer depois do check-in."
            )

        room = self._repository.get_room_for_update(reservation.room_id)
        if room is None:
            raise StayStateConflictError("O quarto da hospedagem não foi encontrado.")
        if room.status != "OCCUPIED":
            raise StayStateConflictError(
                "O quarto não está marcado como ocupado."
            )

        reservation.status = "CHECKED_OUT"
        reservation.actual_check_out_at = current_time
        room.status = "CLEANING"
        self._commit()
        return self._get_view(reservation_id)

    def _commit(self) -> None:
        try:
            self._repository.commit()
        except IntegrityError:
            self._repository.rollback()
            raise

    def _get_view(self, reservation_id: int) -> StayOperationView:
        record = self._repository.get_record(reservation_id)
        if record is None:
            raise StayNotFoundError("Hospedagem não encontrada.")
        return self._to_view(record)

    @staticmethod
    def _to_view(record: StayRecord) -> StayOperationView:
        labels = {
            "CONFIRMED": "Check-in previsto",
            "CHECKED_IN": "Hospedagem ativa",
            "CHECKED_OUT": "Hospedagem finalizada",
        }
        reservation = record.reservation
        return StayOperationView(
            reservation_id=reservation.id,
            guest_name=record.guest_name,
            room_number=record.room_number,
            check_in_date=reservation.check_in_date,
            check_out_date=reservation.check_out_date,
            status=reservation.status,
            status_label=labels.get(reservation.status, reservation.status),
            actual_check_in_at=reservation.actual_check_in_at,
            actual_check_out_at=reservation.actual_check_out_at,
        )
