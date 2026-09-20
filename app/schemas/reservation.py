from datetime import date

from pydantic import BaseModel, Field, model_validator


class ReservationWriteRequest(BaseModel):
    guest_id: int = Field(gt=0)
    room_id: int = Field(gt=0)
    check_in_date: date
    check_out_date: date
    guest_count: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_date_range(self) -> "ReservationWriteRequest":
        if self.check_out_date <= self.check_in_date:
            raise ValueError("Check-out date must be after check-in date.")
        return self


class ReservationView(BaseModel):
    id: int
    guest_id: int
    guest_name: str
    room_id: int
    room_number: str
    check_in_date: date
    check_out_date: date
    guest_count: int
    status: str
    status_label: str
    status_style: str
    period: str


class ReservationGuestOption(BaseModel):
    id: int
    name: str


class ReservationRoomOption(BaseModel):
    id: int
    number: str
    category: str
    capacity: int


class ReservationFormData(BaseModel):
    guests: list[ReservationGuestOption]
    rooms: list[ReservationRoomOption]
    reservation: ReservationView | None = None
