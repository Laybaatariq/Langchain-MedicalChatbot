"""
Fast safety helpers that need no LLM:
  - find_red_flag(): checks a message against the phrases in data/rules/red_flags.json
  - is_informational(): tells "what causes a stroke?" (a general question) apart from
    "my father has a stroke" (a real situation)
  - guess_language() and emergency_message(): the fixed emergency text in the patient's language
"""
import re
from functools import lru_cache

from app.core.config import get_settings
from app.core.knowledge import load_red_flags

settings = get_settings()

_EMERGENCY_URDU = (
    "یہ طبی ایمرجنسی ہو سکتی ہے۔ براہِ کرم فوراً اپنے ملک کے ایمرجنسی نمبر پر کال کریں "
    "یا قریبی ہسپتال کی ایمرجنسی میں جائیں۔"
)
_EMERGENCY_ROMAN_URDU = (
    "Ye ek medical emergency ho sakti hai. Meharbani karke foran apne mulk ke emergency number "
    "par call karein ya qareebi hospital ke emergency mein jayein."
)


def emergency_message(language: str) -> str:
    if language == "urdu":
        return _EMERGENCY_URDU
    if language == "roman_urdu":
        return _EMERGENCY_ROMAN_URDU
    return settings.emergency_default_message


def _normalize(text: str) -> str:
    text = text.lower().replace("\u2019", "'").replace("\u2018", "'")
    return re.sub(r"\s+", " ", text).strip()


@lru_cache
def _matcher(level: str):
    """Returns (compiled regex, {normalized keyword: flag}) for 'emergency' or 'urgent'."""
    lookup: dict[str, dict] = {}
    for flag in load_red_flags()[level]:
        for keyword in flag["keywords"]:
            lookup[_normalize(keyword)] = flag
    ordered = sorted(lookup, key=len, reverse=True)  # longest phrase first
    pattern = re.compile(r"(?<!\w)(?:" + "|".join(re.escape(k) for k in ordered) + r")(?!\w)")
    return pattern, lookup


def find_red_flag(text: str, level: str = "emergency") -> dict | None:
    """Returns the matching red-flag entry (id, label, keywords) or None."""
    if not text:
        return None
    pattern, lookup = _matcher(level)
    match = pattern.search(_normalize(text))
    return lookup[match.group(0)] if match else None


# ---------------------------------------------------------------- informational vs personal
_INFO_PATTERN = re.compile(
    r"^(?:what|how|why|which|when|can|could|does|do|is|are|tell me about|explain|define)\b"
    r"|\b(?:symptoms? of|signs? of|causes? of|risk factors? (?:of|for)|prevent\w*|treatment (?:of|for))\b"
    r"|\bkya (?:hota )?hai\b|\bkyun hota\b|\bkaise (?:bach|roka)",
    re.IGNORECASE,
)

# Words that suggest a real person is affected, or that it is happening now
_PERSONAL_WORDS = {
    "i", "i'm", "im", "ive", "i've", "my", "me", "mine", "we", "our", "he", "she", "his", "her", "him",
    "someone", "somebody", "person", "father", "mother", "dad", "mom", "mum", "baby", "child", "kid",
    "son", "daughter", "wife", "husband", "friend", "patient", "brother", "sister", "grandfather",
    "grandmother", "now", "suddenly", "just", "emergency", "help", "if", "while",
    "mujhe", "mujhay", "mujhko", "mera", "meri", "mere", "hamein", "humein", "abbu", "abu", "ammi",
    "ami", "bhai", "behan", "beta", "beti", "bacha", "bachay", "bachi", "shohar", "biwi", "dost",
    "abhi", "achanak",
}


def is_informational(text: str) -> bool:
    """True for general/educational questions that do not describe a current situation."""
    if not _INFO_PATTERN.search(text):
        return False
    words = set(re.findall(r"[a-z']+", _normalize(text)))
    return not (words & _PERSONAL_WORDS)


# ---------------------------------------------------------------- language guess
_ROMAN_URDU_WORDS = {
    "mein", "hai", "hain", "hoon", "nahi", "nahin", "kya", "kyun", "kaise", "ko", "se", "aur",
    "mujhe", "mujhay", "mera", "meri", "mere", "dard", "bukhar", "khansi", "ulti", "pait", "sar",
    "seene", "saans", "karna", "karein", "kare", "raha", "rahi", "rahe", "tha", "thi", "bohat",
    "bahut", "zyada", "thora", "thori", "abhi", "kitna", "kitne", "kab", "kahan", "koi", "kuch",
    "aap", "hum", "tum", "ye", "yeh", "wo", "woh", "ilaj", "dawai", "bataein", "batayein",
    "chahiye", "lag", "gaya", "gayi",
}


def guess_language(text: str) -> str:
    """Cheap guess: 'urdu' (Arabic script), 'roman_urdu' or 'english'."""
    if re.search(r"[\u0600-\u06FF]", text):
        return "urdu"
    words = re.findall(r"[a-z']+", _normalize(text))
    hits = sum(1 for w in words if w in _ROMAN_URDU_WORDS)
    return "roman_urdu" if hits >= 2 else "english"