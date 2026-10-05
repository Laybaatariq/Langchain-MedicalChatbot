"""
Reads a new message (plus the last few turns) and decides, in ONE LLM call:
  - intent:        medical | chitchat | off_topic
  - language:      english | roman_urdu | urdu
  - english_query: a standalone English search query (resolves "it/this", translates Urdu)
  - urgency:       emergency | sensitive | normal

If the call or the parsing fails, safe defaults are returned with ok=False so the
caller can fall back to plain keyword checks.
"""
import json
import re
from dataclasses import dataclass

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

from app.core.config import get_settings
from app.safety.emergency import guess_language

settings = get_settings()

_INTENTS = {"medical", "chitchat", "off_topic"}
_LANGUAGES = {"english", "roman_urdu", "urdu"}
_URGENCIES = {"emergency", "sensitive", "normal"}

_router_llm = ChatGroq(
    model=settings.llm_model_name,
    temperature=0.0,  # consistent, deterministic routing
    api_key=settings.groq_api_key,
)

_ROUTER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You analyse messages sent to a medical information assistant.
Return ONLY a JSON object with exactly these four keys: intent, language, english_query, urgency. No other text.

intent
- "medical": any question about health, symptoms, conditions, medicines, the body, doctors or hospitals. A short follow-up that depends on the earlier conversation counts as medical when the topic is health.
- "chitchat": greetings, thanks, goodbyes, "who are you", "what can you do", small talk.
- "off_topic": anything else (sports, coding, politics, and so on).

language: the language of the NEW message.
- "roman_urdu": Urdu or Hindi written in English letters (English words inside such a sentence do not change this).
- "urdu": Urdu written in Urdu script.
- "english": English.

english_query: for medical messages, rewrite the new message as a short, standalone English search query. Resolve words like "it", "this" or "that" using the conversation. Translate if the message is not English. Keep the medical terms and drop filler. For other intents, copy the message.

urgency
- "emergency": ONLY when the person describes a situation happening now to them or someone with them that may threaten life (for example chest pain with trouble breathing, stroke signs, severe bleeding, unconsciousness, a seizure, suicidal thoughts, an overdose, a severe allergic reaction). General or educational questions about these topics (for example "what causes a stroke?") are "normal". If you are unsure whether a described current situation is life-threatening, choose "emergency".
- "sensitive": the person asks for a diagnosis, a medicine dose or a prescription.
- "normal": everything else."""),
    ("human", "Recent conversation (oldest first):\n{history}\n\nNew message:\n{message}"),
])

_router_chain = _ROUTER_PROMPT | _router_llm | StrOutputParser()


@dataclass
class Route:
    intent: str = "medical"
    language: str = "english"
    english_query: str = ""
    urgency: str = "normal"
    ok: bool = True  # False when the LLM call or its parsing failed (defaults were used)


def _format_history(history: list[dict] | None, turns: int = 4) -> str:
    lines = []
    for item in (history or [])[-turns:]:
        speaker = "User" if item.get("role") == "user" else "Assistant"
        lines.append(f"{speaker}: {str(item.get('content', ''))[:300]}")
    return "\n".join(lines) if lines else "(none)"


def _parse(raw: str, message: str) -> Route | None:
    match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None

    intent = str(data.get("intent", "")).strip().lower()
    language = str(data.get("language", "")).strip().lower()
    urgency = str(data.get("urgency", "")).strip().lower()
    english_query = str(data.get("english_query", "")).strip()

    return Route(
        intent=intent if intent in _INTENTS else "medical",
        language=language if language in _LANGUAGES else guess_language(message),
        english_query=english_query or message,
        urgency=urgency if urgency in _URGENCIES else "normal",
        ok=True,
    )


def route_message(message: str, history: list[dict] | None = None) -> Route:
    """Never raises. On any failure returns safe defaults with ok=False."""
    try:
        raw = _router_chain.invoke({"history": _format_history(history), "message": message})
        route = _parse(raw, message)
        if route is not None:
            return route
    except Exception as exc:
        print(f"[router] failed, using defaults: {exc}")

    return Route(language=guess_language(message), english_query=message, ok=False)