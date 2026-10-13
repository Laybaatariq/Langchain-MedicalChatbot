"""Builds the short symptom summary a patient can choose to share with the doctor."""
from app.intake import store as intake_store


def build_intake_summary(session_id: str) -> dict | None:
    """
    The finished intake of this chat session as a small dict (English values), or None
    if there is no finished intake. Only fields the patient answered are included.
    """
    try:
        state = intake_store.get_any(session_id)
    except Exception as exc:
        print(f"[booking] could not read the intake: {exc}")
        return None
    if not state or state.get("status") != "done":
        return None

    answers = state.get("answers", {})
    result = state.get("result", {})
    summary = {
        "complaint": answers.get("chief_complaint"),
        "complaint_in_english": state.get("chief_en"),
        "duration": answers.get("duration"),
        "severity": answers.get("severity"),
        "trend": answers.get("trend"),
        "other_symptoms": answers.get("associated"),
        "age": answers.get("age"),
        "urgency": result.get("urgency"),
        "suggested_specialty": result.get("specialty"),
    }
    summary = {k: v for k, v in summary.items() if v not in (None, "", [])}
    return summary or None