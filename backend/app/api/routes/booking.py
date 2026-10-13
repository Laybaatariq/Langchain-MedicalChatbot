from fastapi import APIRouter, Depends, HTTPException

from app.api.booking_schemas import AppointmentOut, AppointmentsResponse, BookRequest, SlotsResponse
from app.auth.deps import current_user
from app.booking import service

router = APIRouter(tags=["Booking"])


def _fail(error: service.BookingError) -> HTTPException:
    return HTTPException(status_code=error.status_code, detail=error.message)


@router.get("/doctors/{doctor_id}/slots", response_model=SlotsResponse)
def doctor_slots(doctor_id: str) -> dict:
    """Free slots for the next 7 days. Public: no login needed to look."""
    try:
        return service.list_slots(doctor_id)
    except service.BookingError as error:
        raise _fail(error)


@router.post("/appointments", response_model=AppointmentOut, status_code=201)
def book_appointment(body: BookRequest, user: dict = Depends(current_user)) -> dict:
    try:
        return service.book(
            user, body.doctor_id, body.start, share_summary=body.share_summary, session_id=body.session_id
        )
    except service.BookingError as error:
        raise _fail(error)


@router.get("/appointments/me", response_model=AppointmentsResponse)
def my_appointments(user: dict = Depends(current_user)) -> dict:
    return service.my_appointments(user)


@router.post("/appointments/{appointment_id}/cancel", response_model=AppointmentOut)
def cancel_appointment(appointment_id: str, user: dict = Depends(current_user)) -> dict:
    try:
        return service.cancel(user, appointment_id)
    except service.BookingError as error:
        raise _fail(error)