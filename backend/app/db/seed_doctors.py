"""
Copies the FICTIONAL sample doctors from doctors.json into MongoDB (collection 'doctors').
Safe to run again: doctors are matched by id and updated, never duplicated.

  python -m app.db.seed_doctors

Uses its own MongoDB connection (same MONGODB_URI as the app), so it does not
depend on how app/db/mongo.py sets up its client.
"""
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from app.core.config import get_settings
from app.core.knowledge import load_doctors

settings = get_settings()


def _connect() -> MongoClient:
    if not settings.mongodb_uri:
        raise SystemExit("MONGODB_URI is not set in backend/.env")

    kwargs = {"serverSelectionTimeoutMS": 15000}
    try:
        import certifi

        kwargs["tlsCAFile"] = certifi.where()
    except ImportError:
        pass

    return MongoClient(settings.mongodb_uri, **kwargs)


def seed() -> None:
    client = _connect()
    try:
        client.admin.command("ping")
    except PyMongoError as exc:
        raise SystemExit(
            f"Could not reach MongoDB Atlas: {exc}\n"
            "Check MONGODB_URI and Atlas Network Access (allow the Codespace IP, or 0.0.0.0/0 for development)."
        )

    collection = client[settings.mongodb_db_name]["doctors"]
    collection.create_index("id", unique=True)
    collection.create_index("specialty")

    doctors = load_doctors()
    for doctor in doctors:
        collection.replace_one({"id": doctor["id"]}, doctor, upsert=True)

    print(f"Seeded {len(doctors)} sample doctors into '{collection.name}'.")
    print(f"Total doctors in the collection: {collection.count_documents({})}")
    client.close()


if __name__ == "__main__":
    seed()