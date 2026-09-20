from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator


class RoomDeviceCreateRequest(BaseModel):
    room_id: int = Field(gt=0)
    code: str = Field(min_length=3, max_length=50)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper()


class RoomDevicePairRequest(BaseModel):
    code: str = Field(min_length=3, max_length=50)
    pairing_code: str = Field(min_length=6, max_length=32)

    @field_validator("code", "pairing_code")
    @classmethod
    def normalize_codes(cls, value: str) -> str:
        return value.strip().upper()


class RoomDeviceView(BaseModel):
    id: int
    code: str
    room_number: str
    active: bool
    provisioned_at: datetime | None
    last_seen_at: datetime | None


class RoomDeviceProvisioningView(RoomDeviceView):
    pairing_code: str
    pairing_expires_at: datetime


class DeviceRoomOption(BaseModel):
    id: int
    number: str


class GuestStayView(BaseModel):
    room_number: str
    room_category: str
    has_active_stay: bool
    guest_name: str | None = None
    check_in_date: date | None = None
    check_out_date: date | None = None
