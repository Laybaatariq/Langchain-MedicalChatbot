"""Request and response shapes for accounts and booking."""
from pydantic import BaseModel, Field

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


# ---------------------------------------------------------------- accounts
class SignupRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    email: str = Field(..., max_length=254, pattern=EMAIL_PATTERN)
    password: str = Field(..., min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: str = Field(..., max_length=254)
    password: str = Field(..., max_length=128)


class UserOut(BaseModel):
    id: str
    name: str
    email: str
    role: str


class AuthResponse(BaseModel):
    token: str
    user: UserOut


# ---------------------------------------------------------------- booking
class SlotOut(BaseModel):
    start: str   # UTC, e.g. 2026-10-14T05:00:00Z
    label: str   # clinic local time, e.g. 10:00


class DayOut(BaseModel):
    date: str
    label: str
    slots: list[SlotOut]


class DoctorBrief(BaseModel):
    id: str
    name: str
    specialty: str
    city: str
    fee_pkr: int


class SlotsResponse(BaseModel):
    doctor: DoctorBrief
    timezone: str
    days: list[DayOut]


class BookRequest(BaseModel):
    doctor_id: str = Field(..., max_length=50)
    start: str = Field(..., max_length=40)
    share_summary: bool = False
    session_id: str | None = Field(default=None, max_length=64)


class AppointmentOut(BaseModel):
    id: str
    doctor_id: str
    doctor_name: str
    specialty: str
    start: str
    start_label: str
    duration_minutes: int
    status: str
    summary_shared: bool
    can_cancel: bool


class AppointmentsResponse(BaseModel):
    upcoming: list[AppointmentOut]
    past: list[AppointmentOut]