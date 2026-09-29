from datetime import datetime, timezone

import dns.resolver
from pymongo import ASCENDING, MongoClient
from pymongo.errors import PyMongoError

from app.core.config import get_settings

settings = get_settings()


def _use_public_dns() -> None:
    """
    Some networks (e.g. mobile hotspots) time out on the SRV/TXT DNS lookups that
    mongodb+srv:// needs. Route those lookups through public DNS servers instead.
    """
    resolver = dns.resolver.Resolver(configure=False)
    resolver.nameservers = ["8.8.8.8", "1.1.1.1"]
    resolver.lifetime = 10
    dns.resolver.default_resolver = resolver


def _build_client() -> MongoClient:
    """Connects to MongoDB Atlas using MONGODB_URI from .env. Fails early if missing."""
    if not settings.mongodb_uri:
        raise RuntimeError("MONGODB_URI must be set in backend/.env (Atlas connection string).")

    if settings.mongodb_uri.startswith("mongodb+srv://"):
        _use_public_dns()

    kwargs = {"serverSelectionTimeoutMS": 10000}

    # certifi fixes TLS certificate errors with Atlas on some Windows setups
    try:
        import certifi

        kwargs["tlsCAFile"] = certifi.where()
    except ImportError:
        pass

    return MongoClient(settings.mongodb_uri, **kwargs)


_client = _build_client()
_db = _client[settings.mongodb_db_name]
_messages = _db[settings.mongodb_chat_collection]


def check_connection() -> bool:
    """Returns True if the Atlas cluster is reachable."""
    try:
        _client.admin.command("ping")
        return True
    except PyMongoError as exc:
        print(f"[MongoDB] Connection failed: {exc}")
        return False


def ensure_indexes() -> None:
    """Index for fast per-session history lookups. Safe to call on every startup."""
    _messages.create_index([("session_id", ASCENDING), ("created_at", ASCENDING)])


def save_message(session_id: str, role: str, content: str, metadata: dict | None = None) -> None:
    """
    Saves one chat message.
    role: "user" or "assistant"
    metadata: optional extras, e.g. {"sources": [...]} for RAG citations
    """
    _messages.insert_one(
        {
            "session_id": session_id,
            "role": role,
            "content": content,
            "metadata": metadata or {},
            "created_at": datetime.now(timezone.utc),
        }
    )


def get_history(session_id: str, limit: int = 20) -> list[dict]:
    """
    Returns the last `limit` messages of a session, oldest first:
    [{"role": "user", "content": "..."}, ...]
    """
    cursor = (
        _messages.find({"session_id": session_id}, {"_id": 0, "role": 1, "content": 1})
        .sort("created_at", -1)
        .limit(limit)
    )
    return list(reversed(list(cursor)))


def clear_history(session_id: str) -> int:
    """Deletes all messages of a session. Returns how many were deleted."""
    return _messages.delete_many({"session_id": session_id}).deleted_count


def list_sessions(limit: int = 50) -> list[dict]:
    """Returns recent sessions with their last activity time, newest first."""
    pipeline = [
        {"$group": {"_id": "$session_id", "last_active": {"$max": "$created_at"}}},
        {"$sort": {"last_active": -1}},
        {"$limit": limit},
    ]
    return [{"session_id": d["_id"], "last_active": d["last_active"]} for d in _messages.aggregate(pipeline)]


# --- Quick manual test ---
#   python -m app.db.mongo
if __name__ == "__main__":
    print("Checking MongoDB Atlas connection...")
    if not check_connection():
        raise SystemExit("Could not reach Atlas. Check MONGODB_URI, Network Access and user password.")
    print("Connected.")

    ensure_indexes()

    print("\nSaving test messages...")
    save_message("test_session", "user", "I have a fever, what should I do?")
    save_message("test_session", "assistant", "Rest, drink fluids, and consult a doctor if it persists.")

    print("\nReading history...")
    for m in get_history("test_session"):
        print(f"- {m['role']}: {m['content']}")

    print(f"\nCleaning up... deleted {clear_history('test_session')} messages.")
    _client.close()