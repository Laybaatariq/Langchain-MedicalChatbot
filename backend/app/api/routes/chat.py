
import uuid
from fastapi import APIRouter, HTTPException

from app.api.schemas import ChatRequest, ChatResponse, SourceCitation
from app.chains.medical_qa_chain import answer_query

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Main chat endpoint. Receives a user message, runs it through the
    full pipeline (triage -> RAG -> LLM), and returns a structured reply.
    """
    try:
        result = answer_query(request.message)
    except Exception as e:
        # Never let the user see raw internal errors — log server-side instead.
        # (Proper logging goes here once logging_config.py is wired up.)
        raise HTTPException(status_code=500, detail="Something went wrong processing your request.") from e

    session_id = request.session_id or str(uuid.uuid4())

    sources = [SourceCitation(**s) for s in result.get("sources", [])]

    return ChatResponse(
        reply=result["reply"],
        category=result["category"],
        sources=sources,
        disclaimer=result.get("disclaimer"),
        session_id=session_id,
    )