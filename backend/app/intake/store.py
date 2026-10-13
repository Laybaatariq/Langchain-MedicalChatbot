"""
Saves the state of a symptom intake in MongoDB (collection 'intake_sessions'),
one document per chat session, so the conversation can continue across requests.

A state document looks like:
  {"_id": session_id, "status": "active" | "done" | "cancelled", "lang": "en" | "ru",
   "flow": [question ids], "index": position of the question being asked,
   "answers": {question id: value}, "chief_en": English version of the complaint,
   "retries": failed attempts on the current question, "result": {...} once finished}

Old documents expire by themselves after 24 hours.
"""
from datetime import datetime, timezone

from app.db.connection import get_db

_COLLECTION = "intake_sessions"
_indexed = False


def _collection():
    global _indexed
    collection = get_db()[_COLLECTION]
    if not _indexed:
        try:
            collection.create_index("updated_at", expireAfterSeconds=24 * 60 * 60)
            _indexed = True
        except Exception as exc:
            print(f"[intake] could not create the expiry index: {exc}")
    return collection


def get_state(session_id: str) -> dict | None:
    """The ACTIVE intake of this session, or None."""
    doc = _collection().find_one({"_id": session_id})
    return doc if doc and doc.get("status") == "active" else None


def get_any(session_id: str) -> dict | None:
    """The intake of this session whatever its status (active, done or cancelled), or None."""
    return _collection().find_one({"_id": session_id})


def save_state(state: dict) -> None:
    state["updated_at"] = datetime.now(timezone.utc)
    _collection().replace_one({"_id": state["_id"]}, state, upsert=True)


def clear_state(session_id: str) -> None:
    _collection().delete_one({"_id": session_id})