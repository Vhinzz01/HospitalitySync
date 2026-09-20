from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


ServiceCategory = Literal["CLEANING", "MAINTENANCE", "HELP", "COMPLAINT"]
ServiceStatus = Literal["OPEN", "IN_PROGRESS", "COMPLETED", "CANCELLED"]


class ServiceRequestCreate(BaseModel):
    category: ServiceCategory
    description: str = Field(min_length=3, max_length=2000)

    @field_validator("description")
    @classmethod
    def strip_description(cls, value: str) -> str:
        return value.strip()


class ServiceRequestStatusUpdate(BaseModel):
    status: ServiceStatus


class ServiceRequestView(BaseModel):
    id: int
    room_number: str
    guest_name: str | None
    category: ServiceCategory
    status: ServiceStatus
    description: str
    created_at: datetime
    completed_at: datetime | None
