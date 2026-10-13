"""
Database access for booking: doctors (read) and appointments (read and write).

Datetimes are stored in MongoDB as naive UTC; the helpers below convert them.

An appointment document:
  {"_id": uuid, "patient_id", "patient_name", "doctor_id", "doctor_name", "specialty",
   "start": naive UTC datetime, "duration_minutes", "status": "confirmed" | "cancelled",
   "intake_summary": dict | None, "created_at", "cancelled_at"?}
"""
from datetime import datetime, timezone

from pymongo.errors import DuplicateKeyError

from app.core.knowledge import load_doctors
from app.db.connection import get_db


class SlotTaken(Exception):
    """Someone else already holds this doctor at this time."""


def to_db(dt: datetime) -> datetime:
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def from_db(dt: datetime) -> datetime:
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def _appointments():
    return get_db()["appointments"]


def ensure_indexes() -> None:
    # Only CONFIRMED appointments count, so a cancelled slot can be booked again.
    _appointments().create_index(
        [("doctor_id", 1), ("start", 1)],
        unique=True,
        partialFilterExpression={"status": "confirmed"},
        name="one_confirmed_per_slot",
    )
    _appointments().create_index([("patient_id", 1), ("start", 1)])


# ---------------------------------------------------------------- doctors
def get_doctor(doctor_id: str) -> dict | None:
    """From MongoDB, or from doctors.json if MongoDB has no such doctor (or cannot be reached)."""
    try:
        doc = get_db()["doctors"].find_one({"id": doctor_id}, {"_id": 0})
        if doc:
            return doc
    except Exception as exc:
        print(f"[booking] could not read the doctor from MongoDB, using the JSON file: {exc}")
    for doctor in load_doctors():
        if doctor["id"] == doctor_id:
            return doctor
    return None


# ---------------------------------------------------------------- appointments
def booked_starts(doctor_id: str, first: datetime, last: datetime) -> set[datetime]:
    """Start times (UTC) already taken for this doctor between `first` and `last`."""
    cursor = _appointments().find(
        {"doctor_id": doctor_id, "status": "confirmed", "start": {"$gte": to_db(first), "$lte": to_db(last)}},
        {"start": 1},
    )
    return {from_db(doc["start"]) for doc in cursor}


def slot_is_taken(doctor_id: str, start: datetime) -> bool:
    return _appointments().count_documents(
        {"doctor_id": doctor_id, "status": "confirmed", "start": to_db(start)}
    ) > 0


def patient_has_slot(patient_id: str, start: datetime) -> bool:
    return _appointments().count_documents(
        {"patient_id": patient_id, "status": "confirmed", "start": to_db(start)}
    ) > 0


def count_upcoming(patient_id: str, now: datetime) -> int:
    return _appointments().count_documents(
        {"patient_id": patient_id, "status": "confirmed", "start": {"$gte": to_db(now)}}
    )


def insert(appointment: dict) -> None:
    """Saves the appointment. The unique index is the final guard against double booking."""
    try:
        _appointments().insert_one(appointment)
    except DuplicateKeyError as exc:
        raise SlotTaken() from exc


def list_for_patient(patient_id: str, limit: int = 100) -> list[dict]:
    return list(_appointments().find({"patient_id": patient_id}).sort("start", -1).limit(limit))


def get_for_patient(appointment_id: str, patient_id: str) -> dict | None:
    return _appointments().find_one({"_id": appointment_id, "patient_id": patient_id})


def mark_cancelled(appointment_id: str, when: datetime) -> None:
    _appointments().update_one(
        {"_id": appointment_id}, {"$set": {"status": "cancelled", "cancelled_at": to_db(when)}}
    )