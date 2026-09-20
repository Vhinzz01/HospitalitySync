from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.food_order_item import FoodOrderItem
    from app.models.reservation import Reservation
    from app.models.room_device import RoomDevice


class FoodOrder(TimestampMixin, Base):
    __tablename__ = "food_orders"
    __table_args__ = (
        CheckConstraint(
            "status IN ('RECEIVED', 'PREPARING', 'READY', 'DELIVERED')",
            name="valid_status",
        ),
        CheckConstraint(
            "(status = 'DELIVERED' AND delivered_at IS NOT NULL) OR "
            "(status <> 'DELIVERED' AND delivered_at IS NULL)",
            name="status_matches_delivered_at",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    reservation_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("reservations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    room_device_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("room_devices.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="RECEIVED",
        server_default="RECEIVED",
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    reservation: Mapped[Reservation] = relationship(back_populates="food_orders")
    room_device: Mapped[RoomDevice] = relationship(back_populates="food_orders")
    items: Mapped[list[FoodOrderItem]] = relationship(back_populates="food_order")
