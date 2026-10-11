"""
Finds doctors for a specialty. Reads the 'doctors' collection in MongoDB and falls
back to data/doctors/doctors.json if MongoDB has none (or cannot be reached).
All doctors in the sample data are fictional.
"""
from app.core.knowledge import load_doctors, load_specialties


def specialty_name(specialty_id: str) -> str:
    for s in load_specialties()["specialties"]:
        if s["id"] == specialty_id:
            return s["name"]
    return specialty_id


def _card(doc: dict) -> dict:
    """What the frontend needs to draw a doctor card."""
    return {
        "id": doc["id"],
        "name": doc["name"],
        "specialty": specialty_name(doc["specialty"]),
        "city": doc["city"],
        "experience_years": doc["experience_years"],
        "fee_pkr": doc["fee_pkr"],
        "modes": doc["modes"],
        "days": doc["schedule"]["days"],
        "is_sample": doc.get("is_sample", True),
    }


def _from_mongo(specialty_id: str, limit: int) -> list[dict]:
    try:
        from app.db.connection import get_db

        cursor = (
            get_db()["doctors"]
            .find({"specialty": specialty_id}, {"_id": 0})
            .sort("experience_years", -1)
            .limit(limit)
        )
        return list(cursor)
    except Exception as exc:
        print(f"[intake] could not read doctors from MongoDB, using the JSON file: {exc}")
        return []


def find_doctors(specialty_id: str, limit: int = 3) -> list[dict]:
    docs = _from_mongo(specialty_id, limit)
    if not docs:
        matching = [d for d in load_doctors() if d["specialty"] == specialty_id]
        docs = sorted(matching, key=lambda d: -d["experience_years"])[:limit]
    return [_card(d) for d in docs]