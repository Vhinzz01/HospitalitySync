from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.food_order import FoodOrder
    from app.models.guest import Guest
    from app.models.room import Room
    from app.models.service_request import ServiceRequest


class Reservation(TimestampMixin, Base):
    __tablename__ = "reservations"
    __table_args__ = (
        CheckConstraint("check_out_date > check_in_date", name="valid_date_range"),
        CheckConstraint("guest_count > 0", name="positive_guest_count"),
        CheckConstraint(
            "status IN ('CONFIRMED', 'CHECKED_IN', 'CHECKED_OUT', 'CANCELLED')",
            name="valid_status",
        ),
        CheckConstraint(
            "actual_check_out_at IS NULL OR "
            "(actual_check_in_at IS NOT NULL AND actual_check_out_at > actual_check_in_at)",
            name="valid_actual_times",
        ),
        CheckConstraint(
            "(status IN ('CONFIRMED', 'CANCELLED') "
            "AND actual_check_in_at IS NULL AND actual_check_out_at IS NULL) OR "
            "(status = 'CHECKED_IN' "
            "AND actual_check_in_at IS NOT NULL AND actual_check_out_at IS NULL) OR "
            "(status = 'CHECKED_OUT' "
            "AND actual_check_in_at IS NOT NULL AND actual_check_out_at IS NOT NULL)",
            name="status_matches_actual_times",
        ),
        ExcludeConstraint(
            ("room_id", "="),
            (func.daterange(text("check_in_date"), text("check_out_date"), "[)"), "&&"),
            where=text("status IN ('CONFIRMED', 'CHECKED_IN')"),
            using="gist",
            name="exclude_overlapping_active_reservations",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    guest_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("guests.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    room_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("rooms.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    check_in_date: Mapped[date] = mapped_column(Date, nullable=False)
    check_out_date: Mapped[date] = mapped_column(Date, nullable=False)
    guest_count: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="CONFIRMED",
        server_default="CONFIRMED",
    )
    actual_check_in_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    actual_check_out_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    guest: Mapped[Guest] = relationship(back_populates="reservations")
    room: Mapped[Room] = relationship(back_populates="reservations")
    food_orders: Mapped[list[FoodOrder]] = relationship(back_populates="reservation")
    service_requests: Mapped[list[ServiceRequest]] = relationship(
        back_populates="reservation"
    )
