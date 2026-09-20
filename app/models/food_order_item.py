from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Identity,
    Integer,
    Numeric,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.food_order import FoodOrder
    from app.models.menu_item import MenuItem


class FoodOrderItem(TimestampMixin, Base):
    __tablename__ = "food_order_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="positive_quantity"),
        CheckConstraint("unit_price >= 0", name="non_negative_unit_price"),
        UniqueConstraint(
            "food_order_id",
            "menu_item_id",
            name="uq_food_order_items_order_menu_item",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    food_order_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("food_orders.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    menu_item_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("menu_items.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    food_order: Mapped[FoodOrder] = relationship(back_populates="items")
    menu_item: Mapped[MenuItem] = relationship(back_populates="order_items")
