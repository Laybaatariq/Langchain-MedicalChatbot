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


def validate() -> list[str]:
    """Returns a list of problems (empty list = everything is consistent)."""
    problems: list[str] = []

    specialty_ids = {s["id"] for s in load_specialties()["specialties"]}
    specialties = load_specialties()
    for key in ("default", "child_specialty"):
        if specialties[key] not in specialty_ids:
            problems.append(f"specialties.json: '{key}' points to unknown specialty '{specialties[key]}'")

    for doctor in load_doctors():
        if doctor["specialty"] not in specialty_ids:
            problems.append(f"doctors.json: {doctor['id']} has unknown specialty '{doctor['specialty']}'")

    intake = load_intake()
    question_ids = {q["id"] for q in intake["questions"]}
    for flow_name, ids in intake["flows"].items():
        for qid in ids:
            if qid not in question_ids:
                problems.append(f"intake_questions.json: flow '{flow_name}' uses unknown question '{qid}'")
    if intake["default_flow"] not in intake["flows"]:
        problems.append("intake_questions.json: default_flow is not one of the flows")

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
    print(f"Intake questions: {len(load_intake()['questions'])}, flows: {list(load_intake()['flows'])}")
    print(f"Sample doctors: {len(load_doctors())}")

    issues = validate()
    if issues:
        print("\nProblems found:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("\nAll files are consistent.")
