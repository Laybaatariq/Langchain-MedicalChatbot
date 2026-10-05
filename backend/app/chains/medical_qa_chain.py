from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_groq import ChatGroq

from app.chains.router import route_message
from app.chains.system_prompts import (
    CHAT_SYSTEM_PROMPT,
    DISCLAIMERS,
    GENERAL_SYSTEM_PROMPT,
    LANGUAGE_NAMES,
    MEDICAL_QA_SYSTEM_PROMPT,
    NOTICES,
    SENSITIVE_EXTRA_RULES,
)
from app.core.config import get_settings
from app.rag.vector_store import similarity_search
from app.safety.emergency import emergency_message, find_red_flag, is_informational
from app.safety.keyword_filters import TriageCategory, regex_pre_filter

settings = get_settings()

# --- Retrieval thresholds (tune them with: python -m app.rag.debug_search "your question") ---
MIN_DOC_SCORE = 0.5     # a passage must score at least this to be used as grounding
SCORE_WINDOW = 0.25     # ...and be within this distance of the best passage
TOP_K = 6               # passages fetched from Qdrant
MAX_PASSAGES = 4        # passages given to the LLM
HISTORY_TURNS = 6       # past messages passed to the LLM

# --- Main answering LLM ---
_answer_llm = ChatGroq(
    model=settings.llm_model_name,
    temperature=settings.llm_temperature,  # 0.1 - grounded, low creativity
    api_key=settings.groq_api_key,
)

_qa_chain = ChatPromptTemplate.from_messages([
    ("system", MEDICAL_QA_SYSTEM_PROMPT),
    MessagesPlaceholder("history"),
    ("human", "Question: {question}\n(Standalone English version: {english_query})"),
]) | _answer_llm | StrOutputParser()

_general_chain = ChatPromptTemplate.from_messages([
    ("system", GENERAL_SYSTEM_PROMPT),
    MessagesPlaceholder("history"),
    ("human", "{question}"),
]) | _answer_llm | StrOutputParser()

_chat_chain = ChatPromptTemplate.from_messages([
    ("system", CHAT_SYSTEM_PROMPT),
    MessagesPlaceholder("history"),
    ("human", "{question}"),
]) | _answer_llm | StrOutputParser()


# ---------------------------------------------------------------- helpers
def _to_messages(history: list[dict] | None) -> list[BaseMessage]:
    """Mongo history ([{"role": "user"|"assistant", "content": ...}]) -> LangChain messages."""
    messages: list[BaseMessage] = []
    for item in (history or [])[-HISTORY_TURNS:]:
        if item["role"] == "user":
            messages.append(HumanMessage(content=item["content"]))
        else:
            messages.append(AIMessage(content=item["content"]))
    return messages


def _select_passages(chunks: list[dict]) -> list[dict]:
    """Keeps only passages that are clearly relevant (score floor + distance from the best)."""
    if not chunks:
        return []
    best = max(c["score"] for c in chunks)
    cutoff = max(MIN_DOC_SCORE, best - SCORE_WINDOW)
    return [c for c in chunks if c["score"] >= cutoff][:MAX_PASSAGES]


def _format_context(passages: list[dict]) -> str:
    return "\n\n".join(f"[Source: {p.get('source', 'unknown')}]\n{p['text']}" for p in passages)


def _body(text: str) -> str:
    """Drops the topic-title header that ingestion puts in front of each chunk."""
    return text.split("\n\n", 1)[-1].strip()


def _to_sources(passages: list[dict]) -> list[dict]:
    """One entry per source (best passage wins), with a link when the chunk has a url."""
    best: dict[str, dict] = {}
    for p in passages:
        key = p.get("source", "Unknown source")
        if key not in best or p["score"] > best[key]["score"]:
            best[key] = p

    ordered = sorted(best.values(), key=lambda p: p["score"], reverse=True)
    return [
        {
            "title": p.get("source", "Unknown source"),
            "snippet": _body(p["text"])[:150] + ("..." if len(_body(p["text"])) > 150 else ""),
            "url": p.get("url"),
            "score": p["score"],
        }
        for p in ordered
    ]


def _response(reply: str, category: str, *, sources=None, disclaimer=None, notice=None, answer_mode="chat") -> dict:
    return {
        "reply": reply,
        "category": category,
        "sources": sources or [],
        "disclaimer": disclaimer,
        "notice": notice,
        "answer_mode": answer_mode,  # "documents" | "general" | "chat" | "emergency"
    }


def _is_emergency(message: str, route) -> bool:
    """
    Emergency if the router says so, or if a red-flag phrase / emergency regex matches.
    A phrase match alone is ignored only for clearly general questions ("what causes a stroke?")
    and only when the router worked and did not flag an emergency.
    """
    if route.urgency == "emergency":
        return True

    keyword_hit = (
        find_red_flag(message) is not None
        or find_red_flag(route.english_query) is not None
        or regex_pre_filter(message) == TriageCategory.EMERGENCY
        or regex_pre_filter(route.english_query) == TriageCategory.EMERGENCY
    )
    if not keyword_hit:
        return False

    return not (route.ok and is_informational(message))


def _is_sensitive(message: str, route) -> bool:
    return (
        route.urgency == "sensitive"
        or regex_pre_filter(message) == TriageCategory.SENSITIVE
        or regex_pre_filter(route.english_query) == TriageCategory.SENSITIVE
    )


# ---------------------------------------------------------------- main entry point
def answer_query(user_message: str, history: list[dict] | None = None) -> dict:
    """
    1. Route the message (intent, language, standalone English query, urgency)
    2. Safety first: emergencies get a fixed message, no LLM answer
    3. Small talk / off-topic -> short friendly reply
    4. Medical question -> answer from the documents if a relevant passage exists,
       otherwise a clearly labelled general-knowledge answer

    Returns a dict matching ChatResponse (minus session_id), see api/schemas.py.
    """
    history = history or []
    route = route_message(user_message, history)
    language_name = LANGUAGE_NAMES.get(route.language, LANGUAGE_NAMES["english"])
    messages = _to_messages(history)

    # --- Safety first ---
    if _is_emergency(user_message, route):
        return _response(
            emergency_message(route.language), TriageCategory.EMERGENCY.value, answer_mode="emergency"
        )

    sensitive = _is_sensitive(user_message, route)
    category = (TriageCategory.SENSITIVE if sensitive else TriageCategory.NORMAL).value
    extra_rules = SENSITIVE_EXTRA_RULES if sensitive else ""
    disclaimer = DISCLAIMERS.get(route.language, DISCLAIMERS["english"])

    # --- Small talk and non-health questions ---
    if route.intent in ("chitchat", "off_topic"):
        reply = _chat_chain.invoke({
            "language_name": language_name,
            "history": messages,
            "question": user_message,
        })
        return _response(reply, category, answer_mode="chat")

    # --- Health question: documents first ---
    passages = _select_passages(similarity_search(route.english_query or user_message, top_k=TOP_K))

    if passages:
        reply = _qa_chain.invoke({
            "language_name": language_name,
            "extra_rules": extra_rules,
            "context": _format_context(passages),
            "history": messages,
            "question": user_message,
            "english_query": route.english_query,
        })
        return _response(
            reply, category,
            sources=_to_sources(passages), disclaimer=disclaimer, answer_mode="documents",
        )

    # --- Nothing relevant in the documents: labelled general answer, no sources ---
    reply = _general_chain.invoke({
        "language_name": language_name,
        "extra_rules": extra_rules,
        "history": messages,
        "question": user_message,
    })
    return _response(
        reply, category,
        disclaimer=disclaimer, notice=NOTICES.get(route.language, NOTICES["english"]), answer_mode="general",
    )


# --- Quick manual test ---
#   python -m app.chains.medical_qa_chain
if __name__ == "__main__":
    test_queries = [
        "hi",
        "chest pain and can't breathe",
        "what causes a stroke?",
        "sar dard ka ilaj kya hai",
        "what helps with a common cold?",
        "who won the cricket world cup?",
    ]

    for q in test_queries:
        print(f"\n{'=' * 50}")
        print(f"Query: {q}")
        result = answer_query(q)
        print(f"Mode: {result['answer_mode']} | Category: {result['category']}")
        print(f"Reply: {result['reply']}")
        if result["notice"]:
            print(f"Notice: {result['notice']}")
        if result["sources"]:
            print(f"Sources: {[(s['title'], round(s['score'], 2)) for s in result['sources']]}")