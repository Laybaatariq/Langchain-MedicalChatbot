import uuid

from fastapi import APIRouter, HTTPException

from app.api.schemas import ChatRequest, ChatResponse
from app.chains.medical_qa_chain import answer_query
from app.db.mongo import clear_history, get_history, save_message
from app.intake.store import clear_state

router = APIRouter()


# Plain `def` (not `async def`): FastAPI runs it in a threadpool, so the
# blocking pymongo / Qdrant / Groq calls don't freeze the server.
@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    session_id = request.session_id or str(uuid.uuid4())

    history = get_history(session_id, limit=10)

    try:
        result = answer_query(request.message, history=history, session_id=session_id)
    except Exception as exc:
        print(f"[chat] error: {exc}")
        raise HTTPException(status_code=500, detail="Something went wrong. Please try again.") from exc

    save_message(session_id, "user", request.message)
    save_message(
        session_id,
        "assistant",
        result["reply"],
        metadata={
            "category": result["category"],
            "answer_mode": result["answer_mode"],
            "urgency": result["urgency"],
            "sources": [s["title"] for s in result["sources"]],
        },
    )

    return ChatResponse(session_id=session_id, **result)


@router.delete("/chat/{session_id}")
def delete_chat(session_id: str) -> dict:
    deleted = clear_history(session_id)
    try:
        clear_state(session_id)  # also forget any running symptom intake
    except Exception as exc:
        print(f"[chat] could not clear the intake state: {exc}")
    return {"deleted": deleted}