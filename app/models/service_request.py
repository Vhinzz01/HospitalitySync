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
    from app.models.reservation import Reservation
    from app.models.room import Room
    from app.models.room_device import RoomDevice
    from app.models.user import User


class ServiceRequest(TimestampMixin, Base):
    __tablename__ = "service_requests"
    __table_args__ = (
        CheckConstraint(
            "category IN ('CLEANING', 'MAINTENANCE', 'HELP', 'COMPLAINT')",
            name="valid_category",
        ),
        CheckConstraint(
            "status IN ('OPEN', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED')",
            name="valid_status",
        ),
        CheckConstraint(
            "NOT (room_device_id IS NOT NULL AND created_by_user_id IS NOT NULL)",
            name="single_creator",
        ),
        CheckConstraint(
            "(status = 'COMPLETED' AND completed_at IS NOT NULL) OR "
            "(status <> 'COMPLETED' AND completed_at IS NULL)",
            name="status_matches_completed_at",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    room_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("rooms.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    reservation_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("reservations.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    room_device_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("room_devices.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    created_by_user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="OPEN",
        server_default="OPEN",
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    room: Mapped[Room] = relationship(back_populates="service_requests")
    reservation: Mapped[Reservation | None] = relationship(
        back_populates="service_requests"
    )
    room_device: Mapped[RoomDevice | None] = relationship(
        back_populates="service_requests"
    )
    created_by_user: Mapped[User | None] = relationship(
        back_populates="created_service_requests"
    )
