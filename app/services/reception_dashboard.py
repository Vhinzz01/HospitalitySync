from __future__ import annotations

from datetime import date

from app.repositories import ReceptionDashboardRepository
from app.schemas import (
    DashboardRoom,
    DashboardSummary,
    ReceptionDashboard,
    RecentReservation,
)


ROOM_STATUS_PRESENTATION = {
    "AVAILABLE": ("Disponível", "available"),
    "OCCUPIED": ("Ocupado", "occupied"),
    "CLEANING": ("Em limpeza", "cleaning"),
    "MAINTENANCE": ("Manutenção", "maintenance"),
}

RESERVATION_STATUS_PRESENTATION = {
    "CONFIRMED": ("Confirmada", "confirmed"),
    "CHECKED_IN": ("Check-in realizado", "checked-in"),
    "CHECKED_OUT": ("Finalizada", "checked-out"),
    "CANCELLED": ("Cancelada", "cancelled"),
}

MONTH_NAMES = (
    "janeiro",
    "fevereiro",
    "março",
    "abril",
    "maio",
    "junho",
    "julho",
    "agosto",
    "setembro",
    "outubro",
    "novembro",
    "dezembro",
)


class ReceptionDashboardService:
    def __init__(self, repository: ReceptionDashboardRepository) -> None:
        self._repository = repository

    def build_dashboard(self, target_date: date | None = None) -> ReceptionDashboard:
        current_date = target_date or date.today()
        summary = DashboardSummary(
            occupied_rooms=self._repository.count_active_rooms_by_status("OCCUPIED"),
            available_rooms=self._repository.count_active_rooms_by_status("AVAILABLE"),
            reservations_today=self._repository.count_reservations_for_date(
                current_date
            ),
            expected_check_ins=self._repository.count_expected_check_ins(current_date),
            expected_check_outs=self._repository.count_expected_check_outs(
                current_date
            ),
            cleaning_requests=self._repository.count_active_service_requests("CLEANING"),
            maintenance_requests=self._repository.count_active_service_requests("MAINTENANCE"),
            complaints=self._repository.count_active_service_requests("COMPLAINT"),
            help_requests=self._repository.count_active_service_requests("HELP"),
            active_food_orders=self._repository.count_active_food_orders(),
        )

        rooms = []
        for room in self._repository.list_active_rooms():
            status_label, status_style = ROOM_STATUS_PRESENTATION[room.status]
            rooms.append(
                DashboardRoom(
                    number=room.number,
                    category=room.category,
                    status=room.status,
                    status_label=status_label,
                    status_style=status_style,
                )
            )

        recent_reservations = []
        for reservation, guest_name, room_number in (
            self._repository.list_recent_reservations()
        ):
            status_label, status_style = RESERVATION_STATUS_PRESENTATION[
                reservation.status
            ]
            recent_reservations.append(
                RecentReservation(
                    guest_name=guest_name,
                    room_number=room_number,
                    period=(
                        f"{reservation.check_in_date:%d/%m/%Y} — "
                        f"{reservation.check_out_date:%d/%m/%Y}"
                    ),
                    status=reservation.status,
                    status_label=status_label,
                    status_style=status_style,
                )
            )

        return ReceptionDashboard(
            date_label=(
                f"{current_date.day} de {MONTH_NAMES[current_date.month - 1]} "
                f"de {current_date.year}"
            ),
            summary=summary,
            rooms=rooms,
            recent_reservations=recent_reservations,
        )
