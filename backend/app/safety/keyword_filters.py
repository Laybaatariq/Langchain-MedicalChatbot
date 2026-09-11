import re
from enum import Enum


class TriageCategory(str, Enum):
    EMERGENCY = "EMERGENCY"
    SENSITIVE = "SENSITIVE"
    NORMAL = "NORMAL"


_EMERGENCY_PATTERNS = re.compile(
    r"\b("
    r"chest pain|difficulty breathing|can't breathe|"
    r"loss of consciousness|stroke|heart attack|"
    r"severe bleeding|suicid|overdose"
    r")\b",
    re.IGNORECASE,
)

_SENSITIVE_PATTERNS = re.compile(
    r"\b("
    r"diagnose|diagnosis|prescription|dosage|dose|"
    r"medication|medicine"
    r")\b",
    re.IGNORECASE,
)


def regex_pre_filter(query: str) -> TriageCategory | None:
    if _EMERGENCY_PATTERNS.search(query):
        return TriageCategory.EMERGENCY

    if _SENSITIVE_PATTERNS.search(query):
        return TriageCategory.SENSITIVE

    return None
