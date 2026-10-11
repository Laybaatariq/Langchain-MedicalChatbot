"""
Loads the rule files and the sample doctors, and checks that they agree with each other.

  python -m app.core.knowledge      # prints counts and checks the files
"""
import json
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
RULES_DIR = DATA_DIR / "rules"
DOCTORS_FILE = DATA_DIR / "doctors" / "doctors.json"


def _read(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


@lru_cache
def load_red_flags() -> dict:
    return _read(RULES_DIR / "red_flags.json")


@lru_cache
def load_specialties() -> dict:
    return _read(RULES_DIR / "specialties.json")


@lru_cache
def load_intake() -> dict:
    return _read(RULES_DIR / "intake_questions.json")


@lru_cache
def load_doctors() -> list[dict]:
    return _read(DOCTORS_FILE)["doctors"]


# ---------------------------------------------------------------- intake helpers
def load_questions() -> dict[str, dict]:
    """Intake questions by id."""
    return {q["id"]: q for q in load_intake()["questions"]}


def load_default_flow_ids() -> list[str]:
    """Question ids of the flow chosen by 'default_flow' (a fresh list every time)."""
    intake = load_intake()
    return list(intake["flows"][intake["default_flow"]])


def load_skip_labels() -> dict[str, str]:
    return load_intake()["skip_label"]


# ---------------------------------------------------------------- checks
def validate() -> list[str]:
    """Returns a list of problems (empty list = everything is consistent)."""
    problems: list[str] = []

    specialties = load_specialties()
    specialty_ids = {s["id"] for s in specialties["specialties"]}
    for key in ("default", "child_specialty"):
        if specialties[key] not in specialty_ids:
            problems.append(f"specialties.json: '{key}' points to unknown specialty '{specialties[key]}'")

    for doctor in load_doctors():
        if doctor["specialty"] not in specialty_ids:
            problems.append(f"doctors.json: {doctor['id']} has unknown specialty '{doctor['specialty']}'")

    intake = load_intake()
    question_ids = {q["id"] for q in intake["questions"]}
    for flow_name, ids in intake["flows"].items():
        if ids and ids[0] != "chief_complaint":
            problems.append(f"intake_questions.json: flow '{flow_name}' must start with 'chief_complaint'")
        for qid in ids:
            if qid not in question_ids:
                problems.append(f"intake_questions.json: flow '{flow_name}' uses unknown question '{qid}'")
    if intake["default_flow"] not in intake["flows"]:
        problems.append("intake_questions.json: default_flow is not one of the flows")

    for q in intake["questions"]:
        for lang in ("en", "ru"):
            if not q.get(lang):
                problems.append(f"intake_questions.json: question '{q['id']}' has no '{lang}' text")
        for option in q.get("options", []):
            for field in ("value", "en", "ru"):
                if not option.get(field):
                    problems.append(f"intake_questions.json: an option of '{q['id']}' is missing '{field}'")
        if q["type"] in ("choice", "multi_choice", "age") and not q.get("options"):
            problems.append(f"intake_questions.json: question '{q['id']}' needs options")
    for lang in ("en", "ru"):
        if not intake["skip_label"].get(lang):
            problems.append(f"intake_questions.json: skip_label has no '{lang}' text")

    seen: set[str] = set()
    for level in ("emergency", "urgent"):
        for flag in load_red_flags()[level]:
            if flag["id"] in seen:
                problems.append(f"red_flags.json: duplicate id '{flag['id']}'")
            seen.add(flag["id"])
            if not flag["keywords"]:
                problems.append(f"red_flags.json: '{flag['id']}' has no keywords")

    return problems


if __name__ == "__main__":
    flags = load_red_flags()
    print(f"Red flags: {len(flags['emergency'])} emergency, {len(flags['urgent'])} urgent")
    print(f"Specialties: {len(load_specialties()['specialties'])}")
    intake = load_intake()
    print(f"Intake questions: {len(intake['questions'])}, flows: {list(intake['flows'])}, default: {intake['default_flow']}")
    print(f"Sample doctors: {len(load_doctors())}")

    issues = validate()
    if issues:
        print("\nProblems found:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("\nAll files are consistent.")