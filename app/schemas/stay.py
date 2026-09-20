from datetime import date, datetime

from pydantic import BaseModel


class StayOperationView(BaseModel):
    reservation_id: int
    guest_name: str
    room_number: str
    check_in_date: date
    check_out_date: date
    status: str
    status_label: str
    actual_check_in_at: datetime | None
    actual_check_out_at: datetime | None
