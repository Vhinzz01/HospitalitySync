from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError

from app.models import RoomDevice, ServiceRequest
from app.repositories import ServiceRequestRecord, ServiceRequestRepository
from app.schemas import (
    ServiceRequestCreate,
    ServiceRequestStatusUpdate,
    ServiceRequestView,
)


class ServiceRequestError(Exception):
    pass


class ServiceRequestNotFoundError(ServiceRequestError):
    pass


class ServiceRequestStateError(ServiceRequestError):
    pass


class ActiveStayRequiredError(ServiceRequestError):
    pass


class ServiceRequestService:
    _transitions = {
        "OPEN": {"IN_PROGRESS", "CANCELLED"},
        "IN_PROGRESS": {"COMPLETED", "CANCELLED"},
        "COMPLETED": set(),
        "CANCELLED": set(),
    }

    def __init__(self, repository: ServiceRequestRepository) -> None:
        self._repository = repository

    def list_for_reception(
        self, category: str | None = None, request_status: str | None = None
    ) -> list[ServiceRequestView]:
        self._validate_filter(category, request_status)
        return [
            self._to_view(record)
            for record in self._repository.list_all(category, request_status)
        ]

    def list_for_device(self, device: RoomDevice) -> list[ServiceRequestView]:
        reservation = self._repository.get_active_reservation(device.room_id)
        if reservation is None:
            return []
        return [
            self._to_view(record)
            for record in self._repository.list_for_reservation(
                device.room_id, reservation.id
            )
        ]

    def create_for_device(
        self, device: RoomDevice, data: ServiceRequestCreate
    ) -> ServiceRequestView:
        reservation = self._repository.get_active_reservation(device.room_id)
        if reservation is None:
            raise ActiveStayRequiredError(
                "É necessário haver uma hospedagem ativa para solicitar um serviço."
            )
        request = ServiceRequest(
            room_id=device.room_id,
            reservation_id=reservation.id,
            room_device_id=device.id,
            category=data.category,
            status="OPEN",
            description=data.description,
        )
        self._repository.add(request)
        try:
            self._repository.commit()
        except IntegrityError:
            self._repository.rollback()
            raise ServiceRequestStateError(
                "Não foi possível registrar a solicitação."
            ) from None
        record = self._repository.get_record(request.id)
        if record is None:
            raise ServiceRequestNotFoundError("Solicitação não encontrada.")
        return self._to_view(record)

    def update_status(
        self, request_id: int, data: ServiceRequestStatusUpdate
    ) -> ServiceRequestView:
        service_request = self._repository.get_for_update(request_id)
        if service_request is None:
            raise ServiceRequestNotFoundError("Solicitação não encontrada.")
        if data.status not in self._transitions[service_request.status]:
            raise ServiceRequestStateError(
                f"Transição de {service_request.status} para {data.status} não permitida."
            )
        service_request.status = data.status
        service_request.completed_at = (
            datetime.now(timezone.utc) if data.status == "COMPLETED" else None
        )
        self._repository.commit()
        record = self._repository.get_record(request_id)
        if record is None:
            raise ServiceRequestNotFoundError("Solicitação não encontrada.")
        return self._to_view(record)

    def get_room_id(self, request_id: int) -> int | None:
        return self._repository.get_room_id(request_id)

    @staticmethod
    def _validate_filter(category: str | None, request_status: str | None) -> None:
        if category and category not in {"CLEANING", "MAINTENANCE", "HELP", "COMPLAINT"}:
            raise ServiceRequestStateError("Categoria de filtro inválida.")
        if request_status and request_status not in {
            "OPEN", "IN_PROGRESS", "COMPLETED", "CANCELLED"
        }:
            raise ServiceRequestStateError("Status de filtro inválido.")

    @staticmethod
    def _to_view(record: ServiceRequestRecord) -> ServiceRequestView:
        item = record.request
        return ServiceRequestView(
            id=item.id,
            room_number=record.room_number,
            guest_name=record.guest_name,
            category=item.category,
            status=item.status,
            description=item.description,
            created_at=item.created_at,
            completed_at=item.completed_at,
        )
