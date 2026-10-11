"""
One shared, lazily created MongoDB connection for the intake feature.

It reads the same MONGODB_URI as the rest of the app but does not depend on how
app/db/mongo.py sets up its own client.
"""
from functools import lru_cache

from pymongo import MongoClient

from app.core.config import get_settings

settings = get_settings()


@lru_cache
def _client() -> MongoClient:
    if not settings.mongodb_uri:
        raise RuntimeError("MONGODB_URI must be set in backend/.env")

    kwargs = {"serverSelectionTimeoutMS": 10000}
    try:
        import certifi

        kwargs["tlsCAFile"] = certifi.where()
    except ImportError:
        pass

    return MongoClient(settings.mongodb_uri, **kwargs)


def get_db():
    """Returns the app's MongoDB database (connects on first use)."""
    return _client()[settings.mongodb_db_name]