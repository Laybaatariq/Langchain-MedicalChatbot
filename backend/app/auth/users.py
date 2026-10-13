"""
User accounts in MongoDB (collection 'users').

  {"_id": uuid string, "name", "email" (lower case, unique), "password_hash",
   "role": "patient", "created_at"}
"""
import uuid
from datetime import datetime, timezone

from pymongo.errors import DuplicateKeyError

from app.db.connection import get_db


class EmailTaken(Exception):
    """An account with this email already exists."""


def _users():
    return get_db()["users"]


def ensure_indexes() -> None:
    _users().create_index("email", unique=True)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def create_user(name: str, email: str, password_hash: str, role: str = "patient") -> dict:
    user = {
        "_id": uuid.uuid4().hex,
        "name": name.strip(),
        "email": normalize_email(email),
        "password_hash": password_hash,
        "role": role,
        "created_at": datetime.now(timezone.utc).replace(tzinfo=None),
    }
    try:
        _users().insert_one(user)
    except DuplicateKeyError as exc:
        raise EmailTaken() from exc
    return user


def find_by_email(email: str) -> dict | None:
    return _users().find_one({"email": normalize_email(email)})


def find_by_id(user_id: str) -> dict | None:
    return _users().find_one({"_id": user_id})


def public(user: dict) -> dict:
    """The parts of a user that are safe to send to the browser (never the password hash)."""
    return {"id": user["_id"], "name": user["name"], "email": user["email"], "role": user["role"]}
