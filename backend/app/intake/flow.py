"""
The symptom-intake conversation, one question at a time.

  start()          called when the router decides the patient is describing symptoms
  handle_answer()  called for every message while an intake is active

Each function returns a response dict shaped like the chat response (see api/schemas.py).
handle_answer() returns None when the patient changed topic, so the normal chat
pipeline can answer instead.
"""
import re

from app.core.knowledge import load_default_flow_ids, load_questions, load_skip_labels
from app.intake import store
from app.intake import texts as T
from app.intake.doctors import find_doctors, specialty_name
from app.intake.rules import compute_urgency, suggest_specialty
from app.safety.emergency import emergency_message, find_red_flag
from app.safety.keyword_filters import TriageCategory, regex_pre_filter

# Choosing one of these always counts as an emergency (conservative on purpose)
EMERGENCY_OPTIONS = {"Chest pain", "Shortness of breath"}

MAX_RETRIES = 2  # failed attempts on one question before the intake is dropped


# ---------------------------------------------------------------- small helpers
def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip(" .!?,")


def _base(reply: str, **extra) -> dict:
    data = {
        "reply": reply,
        "category": TriageCategory.NORMAL.value,
        "sources": [],
        "disclaimer": None,
        "notice": None,
        "answer_mode": "intake",
        "quick_replies": None,
        "progress": None,
        "doctors": [],
        "urgency": None,
        "urgency_label": None,
    }
    data.update(extra)
    return data


def _is_emergency_text(text: str) -> bool:
    return find_red_flag(text) is not None or regex_pre_filter(text) == TriageCategory.EMERGENCY


def _applies(question: dict, answers: dict) -> bool:
    """Some questions are only asked when an earlier answer makes them relevant."""
    cond = question.get("ask_if")
    if not cond:
        return True
    if "sex" in cond and answers.get("sex") != cond["sex"]:
        return False
    age = answers.get("age")
    if "age_min" in cond and (age is None or age < cond["age_min"]):
        return False
    if "age_max" in cond and (age is None or age > cond["age_max"]):
        return False
    return True


def _advance(state: dict, start: int) -> int:
    """Index of the next question to ask, starting at `start` and skipping irrelevant ones."""
    questions = load_questions()
    i = start
    while i < len(state["flow"]) and not _applies(questions[state["flow"][i]], state["answers"]):
        i += 1
    return i


# ---------------------------------------------------------------- asking
def _quick_replies(question: dict, lang: str) -> dict:
    skip = load_skip_labels()[lang] if question.get("skippable") else None
    kind = question["type"]

    if kind in ("choice", "age"):
        return {"mode": "single", "options": [o[lang] for o in question["options"]], "skip_label": skip}
    if kind == "multi_choice":
        return {
            "mode": "multi",
            "options": [o[lang] for o in question["options"]],
            "confirm_label": T.CONFIRM[lang],
            "skip_label": skip,
        }
    if kind == "scale":
        numbers = [str(n) for n in range(question["min"], question["max"] + 1)]
        return {"mode": "single", "options": numbers, "skip_label": skip}
    return {"mode": "text", "options": [], "skip_label": skip}  # free text


def _ask(state: dict, prefix: str | None = None) -> dict:
    lang = state["lang"]
    question = load_questions()[state["flow"][state["index"]]]
    n, total = state["index"] + 1, len(state["flow"])
    text = "\n\n".join(part for part in (prefix, question[lang]) if part)
    return _base(
        text,
        quick_replies=_quick_replies(question, lang),
        progress={"current": n, "total": total, "label": T.PROGRESS[lang].format(n=n, total=total)},
    )


# ---------------------------------------------------------------- reading answers
def _match_option(question: dict, text: str) -> dict | None:
    wanted = _norm(text)
    for option in question.get("options", []):
        if wanted in {_norm(option["en"]), _norm(option["ru"]), _norm(option["value"])}:
            return option
    return None


def _parse_duration(question: dict, text: str):
    option = _match_option(question, text)
    if option:
        return True, option["value"], option

    m = re.search(r"(\d+)\s*(day|days|din|week|weeks|hafta|hafte|month|months|mahina|mahine)", text.lower())
    if not m:
        return False, None, None
    n, unit = int(m.group(1)), m.group(2)
    days = n * (7 if unit.startswith(("week", "haf")) else 30 if unit.startswith(("month", "mahin")) else 1)
    if days <= 3:
        value = "1 to 3 days"
    elif days <= 7:
        value = "4 to 7 days"
    elif days <= 30:
        value = "More than a week"
    else:
        value = "More than a month"
    return True, value, _match_option(question, value)


def _parse(question: dict, text: str):
    """Returns (ok, value, matched_option)."""
    kind = question["type"]

    if kind == "text":
        return bool(text.strip()), text.strip(), None

    if kind == "choice":
        if question["id"] == "duration":
            return _parse_duration(question, text)
        option = _match_option(question, text)
        return (option is not None), (option["value"] if option else None), option

    if kind == "scale":
        m = re.search(r"\b(10|[1-9])\b", text)
        return (m is not None), (int(m.group(1)) if m else None), None

    if kind == "age":
        option = _match_option(question, text)
        if option:
            return True, int(option["value"]), option
        m = re.search(r"\d{1,3}", text)
        if not m:
            return False, None, None
        lowered = text.lower()
        age = 0 if ("month" in lowered or "mahin" in lowered) else min(int(m.group()), 120)
        return True, age, None

    if kind == "multi_choice":
        parts = [p for p in re.split(r"[,;/]| and | aur ", text, flags=re.IGNORECASE) if p.strip()]
        values: list[str] = []
        for part in parts:
            option = _match_option(question, part)
            if option and option["value"] not in values:
                values.append(option["value"])
        if not values:
            return False, None, None
        return True, ([] if "None of these" in values else values), None

    return False, None, None


def _is_skip(text: str, lang: str) -> bool:
    return _norm(text) in {"skip", _norm(load_skip_labels()["en"]), _norm(load_skip_labels()["ru"])}


def _looks_like_new_question(text: str) -> bool:
    return text.strip().endswith("?") or len(text.split()) >= 5


# ---------------------------------------------------------------- finishing
def _display(question: dict, value, lang: str) -> str:
    """Canonical value -> the label in the patient's language."""
    for option in question.get("options", []):
        if option["value"] == value:
            return option[lang]
    return str(value)


def _summary(state: dict) -> str:
    lang, answers = state["lang"], state["answers"]
    questions = load_questions()
    lines = []

    def add(key: str, text: str):
        lines.append(f"- {T.FIELDS[key][lang]}: {text}")

    if answers.get("chief_complaint"):
        add("problem", answers["chief_complaint"])
    if answers.get("duration"):
        add("duration", _display(questions["duration"], answers["duration"], lang))
    if answers.get("severity") is not None:
        add("severity", f"{answers['severity']}/10")
    if answers.get("trend"):
        add("trend", _display(questions["trend"], answers["trend"], lang))
    if answers.get("associated"):
        add("associated", ", ".join(_display(questions["associated"], v, lang) for v in answers["associated"]))
    if answers.get("age_label"):
        add("age", answers["age_label"])
    return "\n".join(lines)


def _finish(state: dict) -> dict:
    lang, answers = state["lang"], state["answers"]
    associated = answers.get("associated") or []
    blob = " ".join([answers.get("chief_complaint", ""), state.get("chief_en", ""), *associated])

    urgency, reasons = compute_urgency(answers, blob)
    specialty_id = suggest_specialty(blob, answers.get("age"))

    doctors = find_doctors(specialty_id)
    fallback = False
    if not doctors:
        doctors = find_doctors("general_physician")
        fallback = True

    parts = [T.OUTCOME[urgency][lang], f"**{T.HEADINGS['summary'][lang]}**\n{_summary(state)}"]
    if reasons:
        bullets = "\n".join(f"- {T.REASONS[key][lang].format(**params)}" for key, params in reasons)
        parts.append(f"**{T.HEADINGS['why'][lang]}**\n{bullets}")
    doctor_line = f"**{T.HEADINGS['doctor_type'][lang]}:** {specialty_name(specialty_id)}"
    if fallback:
        doctor_line += "\n" + T.FALLBACK_NOTE[lang].format(name=specialty_name(specialty_id))
    parts.append(doctor_line)
    parts.append(T.FOOTER[lang])

    state["status"] = "done"
    state["result"] = {"urgency": urgency, "specialty": specialty_id, "reasons": [k for k, _ in reasons]}
    store.save_state(state)

    return _base(
        "\n\n".join(parts),
        doctors=doctors,
        urgency=urgency,
        urgency_label=T.URGENCY_LABEL[urgency][lang],
    )


def _emergency(state: dict) -> dict:
    state["status"] = "cancelled"
    store.save_state(state)
    return _base(
        emergency_message(T.EMERGENCY_LANGUAGE[state["lang"]]),
        category=TriageCategory.EMERGENCY.value,
        answer_mode="emergency",
    )


# ---------------------------------------------------------------- public API
def start(session_id: str, message: str, route) -> dict:
    """The patient's first message already answers question 1 (the complaint)."""
    flow = load_default_flow_ids()
    state = {
        "_id": session_id,
        "status": "active",
        "lang": T.lang_of(route.language),
        "flow": flow,
        "index": 0,
        "answers": {"chief_complaint": message.strip()},
        "chief_en": route.english_query,
        "retries": 0,
    }
    state["index"] = _advance(state, 1)

    if state["index"] >= len(flow):  # a flow with only the complaint question
        return _finish(state)

    store.save_state(state)
    return _ask(state, prefix=T.INTRO[state["lang"]])


def handle_answer(state: dict, message: str) -> dict | None:
    lang = state["lang"]
    text = message.strip()

    # 1. The patient wants to stop
    if _norm(text) in T.CANCEL_WORDS:
        state["status"] = "cancelled"
        store.save_state(state)
        return _base(T.CANCELLED[lang])

    # 2. Safety first, after every answer
    if _is_emergency_text(text):
        return _emergency(state)

    question = load_questions()[state["flow"][state["index"]]]

    # 3. Read the answer
    if question.get("skippable") and _is_skip(text, lang):
        ok, value, option = True, None, None
    else:
        ok, value, option = _parse(question, text)

    if not ok:
        # Looks like a different question: drop the intake and let the normal chat answer
        if _looks_like_new_question(text) or state["retries"] >= MAX_RETRIES:
            state["status"] = "cancelled"
            store.save_state(state)
            return None
        state["retries"] += 1
        store.save_state(state)
        return _ask(state, prefix=T.REASK[question["type"]][lang])

    # 4. Save it
    state["answers"][question["id"]] = value
    state["retries"] = 0
    if question["type"] == "age" and value is not None:
        state["answers"]["age_label"] = option[lang] if option else f"{value}"

    if question["id"] == "associated" and EMERGENCY_OPTIONS & set(value or []):
        return _emergency(state)

    # 5. Next question, or the result
    state["index"] = _advance(state, state["index"] + 1)
    if state["index"] >= len(state["flow"]):
        return _finish(state)

    store.save_state(state)
    return _ask(state)