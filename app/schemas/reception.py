from pydantic import BaseModel


class DashboardSummary(BaseModel):
    occupied_rooms: int
    available_rooms: int
    reservations_today: int
    expected_check_ins: int
    expected_check_outs: int
    cleaning_requests: int
    maintenance_requests: int
    complaints: int
    help_requests: int
    active_food_orders: int


class DashboardRoom(BaseModel):
    number: str
    category: str
    status: str
    status_label: str
    status_style: str


class RecentReservation(BaseModel):
    guest_name: str
    room_number: str
    period: str
    status: str
    status_label: str
    status_style: str


class ReceptionDashboard(BaseModel):
    date_label: str
    summary: DashboardSummary
    rooms: list[DashboardRoom]
    recent_reservations: list[RecentReservation]
