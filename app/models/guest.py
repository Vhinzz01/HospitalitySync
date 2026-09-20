from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, ForeignKey, Identity, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.reservation import Reservation
    from app.models.user import User


class Guest(TimestampMixin, Base):
    __tablename__ = "guests"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
        unique=True,
    )
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    document: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    user: Mapped[User | None] = relationship(back_populates="guest")
    reservations: Mapped[list[Reservation]] = relationship(back_populates="guest")
