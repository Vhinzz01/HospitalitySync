from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Identity, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.reservation import Reservation
    from app.models.room_device import RoomDevice
    from app.models.service_request import ServiceRequest


class Room(TimestampMixin, Base):
    __tablename__ = "rooms"
    __table_args__ = (
        CheckConstraint("capacity > 0", name="positive_capacity"),
        CheckConstraint(
            "status IN ('AVAILABLE', 'OCCUPIED', 'CLEANING', 'MAINTENANCE')",
            name="valid_status",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    number: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="AVAILABLE",
        server_default="AVAILABLE",
    )
    active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    devices: Mapped[list[RoomDevice]] = relationship(back_populates="room")
    reservations: Mapped[list[Reservation]] = relationship(back_populates="room")
    service_requests: Mapped[list[ServiceRequest]] = relationship(back_populates="room")
