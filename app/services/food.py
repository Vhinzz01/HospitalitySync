from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.exc import IntegrityError

from app.models import FoodOrder, FoodOrderItem, MenuItem, RoomDevice
from app.repositories import FoodOrderRecord, FoodRepository
from app.schemas import (
    FoodOrderCreate,
    FoodOrderItemView,
    FoodOrderStatusUpdate,
    FoodOrderView,
    MenuItemAvailability,
    MenuItemView,
    MenuItemWrite,
)


class FoodError(Exception):
    pass


class MenuItemNotFoundError(FoodError):
    pass


class FoodOrderNotFoundError(FoodError):
    pass


class FoodOrderValidationError(FoodError):
    pass


class FoodOrderStateError(FoodError):
    pass


class FoodService:
    _transitions = {
        "RECEIVED": "PREPARING",
        "PREPARING": "READY",
        "READY": "DELIVERED",
        "DELIVERED": None,
    }

    def __init__(self, repository: FoodRepository) -> None:
        self._repository = repository

    def list_menu(self, available_only: bool = False) -> list[MenuItemView]:
        return [self._menu_view(item) for item in self._repository.list_menu(available_only)]

    def create_menu_item(self, data: MenuItemWrite) -> MenuItemView:
        item = MenuItem(**data.model_dump())
        self._repository.add(item)
        self._commit_or_validation_error()
        return self._menu_view(item)

    def update_menu_item(self, item_id: int, data: MenuItemWrite) -> MenuItemView:
        item = self._repository.get_menu_item(item_id)
        if item is None:
            raise MenuItemNotFoundError("Item do cardápio não encontrado.")
        for field, value in data.model_dump().items():
            setattr(item, field, value)
        self._commit_or_validation_error()
        return self._menu_view(item)

    def set_menu_item_availability(
        self, item_id: int, data: MenuItemAvailability
    ) -> MenuItemView:
        item = self._repository.get_menu_item(item_id)
        if item is None:
            raise MenuItemNotFoundError("Item do cardápio não encontrado.")
        item.available = data.available
        self._repository.commit()
        return self._menu_view(item)

    def create_order(self, device: RoomDevice, data: FoodOrderCreate) -> FoodOrderView:
        reservation = self._repository.get_active_reservation(device.room_id)
        if reservation is None:
            raise FoodOrderStateError(
                "É necessário haver uma hospedagem ativa para fazer um pedido."
            )
        item_ids = [line.menu_item_id for line in data.items]
        if len(item_ids) != len(set(item_ids)):
            raise FoodOrderValidationError(
                "Cada item deve aparecer somente uma vez no pedido."
            )
        menu_items = {item.id: item for item in self._repository.get_menu_items(set(item_ids))}
        if len(menu_items) != len(item_ids):
            raise MenuItemNotFoundError("Um ou mais itens do cardápio não existem.")
        if any(not menu_items[item_id].available for item_id in item_ids):
            raise FoodOrderStateError("Um ou mais itens não estão disponíveis.")

        order = FoodOrder(
            reservation_id=reservation.id,
            room_device_id=device.id,
            status="RECEIVED",
            notes=data.notes,
        )
        self._repository.add(order)
        try:
            self._repository.flush()
            for line in data.items:
                menu_item = menu_items[line.menu_item_id]
                self._repository.add(
                    FoodOrderItem(
                        food_order_id=order.id,
                        menu_item_id=menu_item.id,
                        quantity=line.quantity,
                        unit_price=menu_item.price,
                    )
                )
            self._repository.commit()
        except IntegrityError:
            self._repository.rollback()
            raise FoodOrderValidationError("Não foi possível registrar o pedido.") from None
        return self.get_order(order.id)

    def list_kitchen_orders(self, order_status: str | None = None) -> list[FoodOrderView]:
        self._validate_status_filter(order_status)
        return [self._order_view(record) for record in self._repository.list_orders(order_status)]

    def list_device_orders(self, device: RoomDevice) -> list[FoodOrderView]:
        reservation = self._repository.get_active_reservation(device.room_id)
        if reservation is None:
            return []
        return [
            self._order_view(record)
            for record in self._repository.list_orders(reservation_id=reservation.id)
        ]

    def get_order(self, order_id: int) -> FoodOrderView:
        record = self._repository.get_order_record(order_id)
        if record is None:
            raise FoodOrderNotFoundError("Pedido não encontrado.")
        return self._order_view(record)

    def update_order_status(
        self, order_id: int, data: FoodOrderStatusUpdate
    ) -> FoodOrderView:
        order = self._repository.get_order_for_update(order_id)
        if order is None:
            raise FoodOrderNotFoundError("Pedido não encontrado.")
        expected = self._transitions[order.status]
        if data.status != expected:
            raise FoodOrderStateError(
                f"Transição de {order.status} para {data.status} não permitida."
            )
        order.status = data.status
        order.delivered_at = (
            datetime.now(timezone.utc) if data.status == "DELIVERED" else None
        )
        self._repository.commit()
        return self.get_order(order_id)

    def get_order_room_id(self, order_id: int) -> int | None:
        return self._repository.get_order_room_id(order_id)

    def _order_view(self, record: FoodOrderRecord) -> FoodOrderView:
        item_views: list[FoodOrderItemView] = []
        total = Decimal("0.00")
        for record_item in self._repository.list_order_items(record.order.id):
            item = record_item.item
            subtotal = item.unit_price * item.quantity
            total += subtotal
            item_views.append(FoodOrderItemView(menu_item_id=item.menu_item_id, name=record_item.menu_item_name, quantity=item.quantity, unit_price=item.unit_price, subtotal=subtotal))
        order = record.order
        return FoodOrderView(id=order.id, room_number=record.room_number, guest_name=record.guest_name, status=order.status, notes=order.notes, items=item_views, total=total, created_at=order.created_at, delivered_at=order.delivered_at)

    def _commit_or_validation_error(self) -> None:
        try:
            self._repository.commit()
        except IntegrityError:
            self._repository.rollback()
            raise FoodOrderValidationError("Dados do cardápio inválidos.") from None

    @staticmethod
    def _validate_status_filter(order_status: str | None) -> None:
        if order_status and order_status not in {"RECEIVED", "PREPARING", "READY", "DELIVERED"}:
            raise FoodOrderValidationError("Status de filtro inválido.")

    @staticmethod
    def _menu_view(item: MenuItem) -> MenuItemView:
        return MenuItemView(id=item.id, name=item.name, description=item.description, price=item.price, available=item.available)
