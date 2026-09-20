from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Identity, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.guest import Guest
    from app.models.service_request import ServiceRequest


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    __table_args__ = (
        CheckConstraint(
            "role IN ('RECEPTION', 'KITCHEN', 'GUEST')",
            name="valid_role",
        ),
        Index("uq_users_email_lower", func.lower(email), unique=True),
    )

    guest: Mapped[Guest | None] = relationship(back_populates="user")
    created_service_requests: Mapped[list[ServiceRequest]] = relationship(
        back_populates="created_by_user"
    )
