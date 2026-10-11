"""
The decision rules of the intake. Pure functions (no database, no LLM), so every
decision can be read, tested and explained.

These rules are a DEMO written for a learning project. They are not clinical rules.
"""
import re

from app.core.knowledge import load_specialties
from app.safety.emergency import find_red_flag

LONG_DURATIONS = {"4 to 7 days", "More than a week", "More than a month"}


def compute_urgency(answers: dict, free_text: str) -> tuple[str, list[tuple[str, dict]]]:
    """
    Returns (level, reasons). level is "urgent", "routine" or "self_care".
    (An emergency never gets here: it is stopped earlier, at every answer.)
    reasons is a list of (key, params) that texts.REASONS can turn into sentences.
    """
    severity = answers.get("severity")
    trend = answers.get("trend")
    duration = answers.get("duration")
    associated = answers.get("associated") or []
    age = answers.get("age")
    has_fever = "Fever" in associated
    long_duration = duration in LONG_DURATIONS

    urgent: list[tuple[str, dict]] = []
    if severity is not None and severity >= 8:
        urgent.append(("severe", {"n": severity}))
    if trend == "Getting worse" and severity is not None and severity >= 6:
        urgent.append(("worsening", {}))
    if has_fever and long_duration:
        urgent.append(("long_fever", {}))
    if has_fever and age is not None and (age < 3 or age >= 65):
        urgent.append(("fever_vulnerable", {}))
    if age is not None and age < 1:
        urgent.append(("infant", {}))
    flag = find_red_flag(free_text, level="urgent")
    if flag:
        urgent.append(("urgent_phrase", {"label": flag["label"]}))
    if urgent:
        return "urgent", urgent

    routine: list[tuple[str, dict]] = []
    if severity is not None and severity >= 5:
        routine.append(("moderate", {"n": severity}))
    if trend == "Getting worse":
        routine.append(("worsening", {}))
    if long_duration:
        routine.append(("long", {}))
    if routine:
        return "routine", routine

    return "self_care", []


def _contains(text: str, phrase: str) -> bool:
    return re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", text) is not None


def suggest_specialty(text: str, age: int | None) -> str:
    """
    Picks the type of doctor from the words the patient used.
    Children go to the pediatrician; if no keyword matches, a General Physician.
    """
    data = load_specialties()

    if age is not None and age < data["child_age_limit"]:
        return data["child_specialty"]

    text = text.lower()
    best_id, best_score = data["default"], 0
    for specialty in data["specialties"]:
        # a multi-word phrase counts for more than a single word
        score = sum(len(k.split()) for k in specialty["symptom_keywords"] if _contains(text, k.lower()))
        if score > best_score:
            best_id, best_score = specialty["id"], score

    return best_id