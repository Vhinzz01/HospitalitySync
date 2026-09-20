from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator


FoodOrderStatus = Literal["RECEIVED", "PREPARING", "READY", "DELIVERED"]


class MenuItemWrite(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    description: str | None = Field(default=None, max_length=2000)
    price: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    available: bool = True

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        return value.strip()

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class MenuItemAvailability(BaseModel):
    available: bool


class MenuItemView(BaseModel):
    id: int
    name: str
    description: str | None
    price: Decimal
    available: bool


class FoodOrderLineCreate(BaseModel):
    menu_item_id: int = Field(gt=0)
    quantity: int = Field(gt=0, le=50)


class FoodOrderCreate(BaseModel):
    items: list[FoodOrderLineCreate] = Field(min_length=1, max_length=30)
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("notes")
    @classmethod
    def normalize_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class FoodOrderStatusUpdate(BaseModel):
    status: FoodOrderStatus


class FoodOrderItemView(BaseModel):
    menu_item_id: int
    name: str
    quantity: int
    unit_price: Decimal
    subtotal: Decimal


class FoodOrderView(BaseModel):
    id: int
    room_number: str
    guest_name: str
    status: FoodOrderStatus
    notes: str | None
    items: list[FoodOrderItemView]
    total: Decimal
    created_at: datetime
    delivered_at: datetime | None
