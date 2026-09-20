from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import FoodOrder, FoodOrderItem, Guest, MenuItem, Reservation, Room


@dataclass(frozen=True, slots=True)
class FoodOrderRecord:
    order: FoodOrder
    room_number: str
    guest_name: str


@dataclass(frozen=True, slots=True)
class FoodOrderItemRecord:
    item: FoodOrderItem
    menu_item_name: str


class FoodRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_menu(self, available_only: bool = False) -> list[MenuItem]:
        statement = select(MenuItem)
        if available_only:
            statement = statement.where(MenuItem.available.is_(True))
        return list(self._session.scalars(statement.order_by(MenuItem.name)))

    def get_menu_item(self, item_id: int) -> MenuItem | None:
        return self._session.get(MenuItem, item_id)

    def get_menu_items(self, item_ids: set[int]) -> list[MenuItem]:
        if not item_ids:
            return []
        return list(self._session.scalars(select(MenuItem).where(MenuItem.id.in_(item_ids))))

    def get_active_reservation(self, room_id: int) -> Reservation | None:
        return self._session.scalar(select(Reservation).where(Reservation.room_id == room_id, Reservation.status == "CHECKED_IN"))

    def list_orders(
        self, order_status: str | None = None, reservation_id: int | None = None
    ) -> list[FoodOrderRecord]:
        statement = (
            select(FoodOrder, Room.number, Guest.full_name)
            .join(Reservation, FoodOrder.reservation_id == Reservation.id)
            .join(Room, Reservation.room_id == Room.id)
            .join(Guest, Reservation.guest_id == Guest.id)
        )
        if order_status:
            statement = statement.where(FoodOrder.status == order_status)
        if reservation_id is not None:
            statement = statement.where(FoodOrder.reservation_id == reservation_id)
        statement = statement.order_by(FoodOrder.created_at.desc())
        return [FoodOrderRecord(*row) for row in self._session.execute(statement)]

    def get_order_for_update(self, order_id: int) -> FoodOrder | None:
        return self._session.scalar(select(FoodOrder).where(FoodOrder.id == order_id).with_for_update())

    def get_order_record(self, order_id: int) -> FoodOrderRecord | None:
        row = self._session.execute(
            select(FoodOrder, Room.number, Guest.full_name)
            .join(Reservation, FoodOrder.reservation_id == Reservation.id)
            .join(Room, Reservation.room_id == Room.id)
            .join(Guest, Reservation.guest_id == Guest.id)
            .where(FoodOrder.id == order_id)
        ).one_or_none()
        return FoodOrderRecord(*row) if row else None

    def get_order_room_id(self, order_id: int) -> int | None:
        return self._session.scalar(
            select(Reservation.room_id)
            .join(FoodOrder, FoodOrder.reservation_id == Reservation.id)
            .where(FoodOrder.id == order_id)
        )

    def list_order_items(self, order_id: int) -> list[FoodOrderItemRecord]:
        statement = (
            select(FoodOrderItem, MenuItem.name)
            .join(MenuItem, FoodOrderItem.menu_item_id == MenuItem.id)
            .where(FoodOrderItem.food_order_id == order_id)
            .order_by(FoodOrderItem.id)
        )
        return [FoodOrderItemRecord(*row) for row in self._session.execute(statement)]

    def add(self, entity: MenuItem | FoodOrder | FoodOrderItem) -> None:
        self._session.add(entity)

    def flush(self) -> None:
        self._session.flush()

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()
