from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.core.config import get_settings
from app.safety.keyword_filters import TriageCategory, regex_pre_filter

settings = get_settings()

# --- LLM instance for classification only ---
# Kept separate from the main answering LLM (in chains/) so we can
# tune it independently (e.g. even lower temperature, smaller model).
_classifier_llm = ChatGroq(
    model=settings.llm_model_name,
    temperature=0.0,  # zero temperature: we want consistent, deterministic classification
    api_key=settings.groq_api_key,
)

_CLASSIFIER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a medical query safety classifier. Classify the user's
message into exactly ONE of these categories:

- EMERGENCY: describes a potentially life-threatening situation (even if
  phrased indirectly), e.g. sudden severe symptoms, suicidal thoughts,
  loss of consciousness, signs of stroke/heart attack.
- SENSITIVE: asks for a direct diagnosis, exact medication dosage, or a
  prescription, without describing an emergency.
- NORMAL: a general health question that can be safely answered with
  grounded, cited information and a disclaimer.

Respond with ONLY one word: EMERGENCY, SENSITIVE, or NORMAL.
When in doubt between EMERGENCY and something else, choose EMERGENCY —
a false alarm is far less costly than missing a real emergency."""),
    ("human", "{query}"),
])

_classifier_chain = _CLASSIFIER_PROMPT | _classifier_llm | StrOutputParser()


def classify_with_llm(text: str) -> TriageCategory:
    """
    Calls the LLM to classify a query that the regex pre-filter
    could not confidently categorize (i.e. returned UNKNOWN).
    """
    raw_result = _classifier_chain.invoke({"query": text}).strip().upper()

    # Defensive parsing: LLM output should be exactly one of our
    # enum values, but we guard against extra whitespace/punctuation.
    if "EMERGENCY" in raw_result:
        return TriageCategory.EMERGENCY
    elif "SENSITIVE" in raw_result:
        return TriageCategory.SENSITIVE
    elif "NORMAL" in raw_result:
        return TriageCategory.NORMAL

    # Fail-safe: if the LLM response is unparseable, default to
    # SENSITIVE rather than NORMAL — safer to over-caution than
    # to let something risky through as a plain answer.
    return TriageCategory.SENSITIVE


def triage(text: str) -> TriageCategory:
    """
    Main entry point for the safety layer. Combines the fast regex
    pre-filter with the LLM classifier fallback.

    Flow:
      1. Try regex first (fast, free, catches obvious cases).
      2. Only call the LLM if regex returns UNKNOWN.
    """
    regex_result = regex_pre_filter(text)

    if regex_result != TriageCategory.UNKNOWN:
        return regex_result

    return classify_with_llm(text)