
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.core.config import get_settings
from app.safety.triage_classifier import triage
from app.safety.keyword_filters import TriageCategory
from app.rag.vector_store import similarity_search
from app.chains.system_prompts import (
    MEDICAL_QA_SYSTEM_PROMPT,
    DISCLAIMER_TEXT,
    CLARIFY_PROMPT,
)

settings = get_settings()

# --- Main answering LLM (separate instance from the triage classifier's LLM) ---
_answer_llm = ChatGroq(
    model=settings.llm_model_name,
    temperature=settings.llm_temperature,  # 0.1 — grounded, low creativity
    api_key=settings.groq_api_key,
)

_qa_prompt = ChatPromptTemplate.from_messages([
    ("system", MEDICAL_QA_SYSTEM_PROMPT),
    ("human", "{question}"),
])

_qa_chain = _qa_prompt | _answer_llm | StrOutputParser()

_clarify_chain = (
    ChatPromptTemplate.from_messages([("human", CLARIFY_PROMPT)])
    | _answer_llm
    | StrOutputParser()
)


def _format_context(retrieved_chunks: list[dict]) -> str:
    """Turns retrieved chunks into a single context string for the prompt."""
    if not retrieved_chunks:
        return "No relevant information found in the knowledge base."

    formatted = []
    for chunk in retrieved_chunks:
        source = chunk.get("source", "unknown")
        formatted.append(f"[Source: {source}]\n{chunk['text']}")

    return "\n\n".join(formatted)


def _is_ambiguous(retrieved_chunks: list[dict], min_score: float = 0.3) -> bool:
    """
    Simple ambiguity check: if the best retrieved chunk has a low
    similarity score, the query is probably too vague to answer well.
    """
    if not retrieved_chunks:
        return True
    return retrieved_chunks[0]["score"] < min_score


def answer_query(user_message: str) -> dict:
    """
    Main entry point for the chatbot. Combines:
      1. Safety triage (emergency / sensitive / normal)
      2. RAG retrieval (grounding context)
      3. LLM generation (with guardrails) OR clarifying question

    Returns a dict matching the shape of ChatResponse (see api/schemas.py).
    """
    category = triage(user_message)

    # --- Case 1: Emergency — never call the LLM, return fixed safe message ---
    if category == TriageCategory.EMERGENCY:
        return {
            "reply": settings.emergency_default_message,
            "category": category.value,
            "sources": [],
            "disclaimer": None,
        }

    # --- Retrieve grounding context for both SENSITIVE and NORMAL cases ---
    retrieved_chunks = similarity_search(user_message, top_k=4)

    # --- Case 2: Query too vague — ask a clarifying question instead of guessing ---
    if _is_ambiguous(retrieved_chunks):
        clarifying_question = _clarify_chain.invoke({"query": user_message})
        return {
            "reply": clarifying_question,
            "category": category.value,
            "sources": [],
            "disclaimer": None,
        }

    # --- Case 3: Normal or Sensitive — answer using grounded context ---
    context = _format_context(retrieved_chunks)
    reply = _qa_chain.invoke({"question": f"Context:\n{context}\n\nQuestion: {user_message}"})

    sources = [
        {
            "title": chunk.get("source", "Unknown source"),
            "snippet": chunk["text"][:150] + "...",
            "url": None,
        }
        for chunk in retrieved_chunks
    ]

    return {
        "reply": reply,
        "category": category.value,
        "sources": sources,
        "disclaimer": DISCLAIMER_TEXT,
    }


# --- Quick manual test ---
#   python -m app.chains.medical_qa_chain
if __name__ == "__main__":
    test_queries = [
        "chest pain and can't breathe",
        "sar dard",
        "what helps with a common cold?",
    ]

    for q in test_queries:
        print(f"\n{'='*50}")
        print(f"Query: {q}")
        result = answer_query(q)
        print(f"Category: {result['category']}")
        print(f"Reply: {result['reply']}")
        if result['sources']:
            print(f"Sources: {[s['title'] for s in result['sources']]}")