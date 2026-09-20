from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.food_order import FoodOrder
    from app.models.room import Room
    from app.models.service_request import ServiceRequest


class RoomDevice(TimestampMixin, Base):
    __tablename__ = "room_devices"
    __table_args__ = (
        CheckConstraint(
            "(pairing_code_hash IS NULL AND pairing_expires_at IS NULL) OR "
            "(pairing_code_hash IS NOT NULL AND pairing_expires_at IS NOT NULL)",
            name="pairing_fields_together",
        ),
        CheckConstraint(
            "active = false OR "
            "(credential_hash IS NOT NULL AND provisioned_at IS NOT NULL)",
            name="active_device_is_provisioned",
        ),
        Index(
            "uq_room_devices_active_room",
            "room_id",
            unique=True,
            postgresql_where=text("active = true"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    room_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("rooms.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    credential_hash: Mapped[str | None] = mapped_column(
        String(255), nullable=True, unique=True
    )
    active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    provisioned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    pairing_code_hash: Mapped[str | None] = mapped_column(
        String(255), nullable=True, unique=True
    )
    pairing_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    room: Mapped[Room] = relationship(back_populates="devices")
    food_orders: Mapped[list[FoodOrder]] = relationship(back_populates="room_device")
    service_requests: Mapped[list[ServiceRequest]] = relationship(
        back_populates="room_device"
    )
