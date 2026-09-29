import re
from enum import Enum


class TriageCategory(str, Enum):
    EMERGENCY = "EMERGENCY"
    SENSITIVE = "SENSITIVE"
    NORMAL = "NORMAL"
    UNKNOWN = "UNKNOWN"  # regex could not decide; the LLM classifier takes over


_EMERGENCY_PATTERNS = re.compile(
    r"\b(?:"
    r"chest pain|difficulty breathing|trouble breathing|shortness of breath|"
    r"can['’]?t breathe|cannot breathe|"
    r"loss of consciousness|unconscious|"
    r"stroke|heart attack|severe bleeding|seizure|"
    r"suicid\w*|kill myself|self[- ]harm|overdose"
    r")\b",
    re.IGNORECASE,
)

_SENSITIVE_PATTERNS = re.compile(
    r"\b(?:"
    r"diagnos\w*|prescri\w*|dosage|doses?|"
    r"medication|medicine"
    r")\b",
    re.IGNORECASE,
)


def regex_pre_filter(query: str) -> TriageCategory:
    """Fast first pass. Returns UNKNOWN when neither pattern matches."""
    if _EMERGENCY_PATTERNS.search(query):
        return TriageCategory.EMERGENCY

    if _SENSITIVE_PATTERNS.search(query):
        return TriageCategory.SENSITIVE

    return TriageCategory.UNKNOWN