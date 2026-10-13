"""
The booking rules: list free slots, book, list my appointments, cancel.
Every rule that can refuse a request raises a BookingError with the HTTP status to use.
"""
import uuid
from datetime import datetime, timedelta, timezone

from app.booking import repo, slots
from app.booking.summary import build_intake_summary
from app.intake.doctors import specialty_name

MAX_UPCOMING = 5   # a patient can hold at most this many future appointments


class BookingError(Exception):
    status_code = 400

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class NotFound(BookingError):
    status_code = 404


class InvalidSlot(BookingError):
    status_code = 422


class LimitReached(BookingError):
    status_code = 422


class Conflict(BookingError):
    status_code = 409


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_start(text: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(text.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise InvalidSlot("The appointment time is not valid.") from exc
    if parsed.tzinfo is None:
        raise InvalidSlot("The appointment time must include a time zone.")
    return parsed.astimezone(timezone.utc)


def present(appointment: dict, now: datetime | None = None) -> dict:
    """An appointment document as the browser should see it (no patient or intake details)."""
    now = now or _utc_now()
    start = repo.from_db(appointment["start"])
    return {
        "id": appointment["_id"],
        "doctor_id": appointment["doctor_id"],
        "doctor_name": appointment["doctor_name"],
        "specialty": specialty_name(appointment["specialty"]),
        "start": slots.iso_z(start),
        "start_label": slots.full_label(start),
        "duration_minutes": appointment["duration_minutes"],
        "status": appointment["status"],
        "summary_shared": bool(appointment.get("intake_summary")),
        "can_cancel": appointment["status"] == "confirmed" and start > now,
    }


# ---------------------------------------------------------------- slots
def list_slots(doctor_id: str, now: datetime | None = None) -> dict:
    now = now or _utc_now()
    doctor = repo.get_doctor(doctor_id)
    if not doctor:
        raise NotFound("Doctor not found.")

    by_day = slots.slots_by_day(doctor["schedule"], now)
    everything = [s for starts in by_day.values() for s in starts]
    taken = repo.booked_starts(doctor_id, min(everything), max(everything)) if everything else set()

    days = []
    for day, starts in sorted(by_day.items()):
        free = [s for s in starts if s not in taken]
        if free:
            days.append({
                "date": day.isoformat(),
                "label": slots.day_label(day),
                "slots": [{"start": slots.iso_z(s), "label": slots.time_label(s)} for s in free],
            })

    return {
        "doctor": {
            "id": doctor["id"],
            "name": doctor["name"],
            "specialty": specialty_name(doctor["specialty"]),
            "city": doctor["city"],
            "fee_pkr": doctor["fee_pkr"],
        },
        "timezone": slots.settings.clinic_timezone,
        "days": days,
    }


# ---------------------------------------------------------------- booking
def book(
    user: dict,
    doctor_id: str,
    start_text: str,
    share_summary: bool = False,
    session_id: str | None = None,
    now: datetime | None = None,
) -> dict:
    now = now or _utc_now()

    doctor = repo.get_doctor(doctor_id)
    if not doctor:
        raise NotFound("Doctor not found.")

    start = _parse_start(start_text)
    valid = {s for starts in slots.slots_by_day(doctor["schedule"], now).values() for s in starts}
    if start not in valid:
        if start < now + timedelta(hours=slots.MIN_LEAD_HOURS):
            raise InvalidSlot(f"Appointments must be booked at least {slots.MIN_LEAD_HOURS} hours ahead.")
        raise InvalidSlot("That time is not available for this doctor. Please pick one of the listed slots.")

    if repo.count_upcoming(user["_id"], now) >= MAX_UPCOMING:
        raise LimitReached(f"You already have {MAX_UPCOMING} upcoming appointments. Please cancel one first.")
    if repo.patient_has_slot(user["_id"], start):
        raise Conflict("You already have an appointment at this time.")
    if repo.slot_is_taken(doctor_id, start):
        raise Conflict("Someone just booked this slot. Please pick another time.")

    summary = build_intake_summary(session_id) if (share_summary and session_id) else None

    appointment = {
        "_id": uuid.uuid4().hex,
        "patient_id": user["_id"],
        "patient_name": user["name"],
        "doctor_id": doctor["id"],
        "doctor_name": doctor["name"],
        "specialty": doctor["specialty"],
        "start": repo.to_db(start),
        "duration_minutes": doctor["schedule"]["slot_minutes"],
        "status": "confirmed",
        "intake_summary": summary,
        "created_at": repo.to_db(now),
    }
    try:
        repo.insert(appointment)
    except repo.SlotTaken as exc:  # lost a race with another patient
        raise Conflict("Someone just booked this slot. Please pick another time.") from exc

    return present(appointment, now)


# ---------------------------------------------------------------- my appointments
def my_appointments(user: dict, now: datetime | None = None) -> dict:
    now = now or _utc_now()
    upcoming, past = [], []
    for doc in repo.list_for_patient(user["_id"]):
        item = present(doc, now)
        is_upcoming = doc["status"] == "confirmed" and repo.from_db(doc["start"]) >= now
        (upcoming if is_upcoming else past).append(item)
    upcoming.sort(key=lambda a: a["start"])   # soonest first
    return {"upcoming": upcoming, "past": past}  # past: newest first (list_for_patient order)


def cancel(user: dict, appointment_id: str, now: datetime | None = None) -> dict:
    now = now or _utc_now()
    doc = repo.get_for_patient(appointment_id, user["_id"])
    if not doc:
        raise NotFound("Appointment not found.")

    if doc["status"] == "cancelled":  # cancelling twice is harmless
        return present(doc, now)
    if repo.from_db(doc["start"]) <= now:
        raise InvalidSlot("Past appointments cannot be cancelled.")

    repo.mark_cancelled(appointment_id, now)
    doc["status"] = "cancelled"
    return present(doc, now)