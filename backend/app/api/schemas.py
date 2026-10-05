from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    # Frontend sends the same session_id on every message of a conversation.
    # If missing, the server creates one and returns it.
    session_id: str | None = None


class SourceCitation(BaseModel):
    title: str
    snippet: str | None = None
    url: str | None = None
    score: float | None = None


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    category: str | None = None
    sources: list[SourceCitation] = Field(default_factory=list)
    disclaimer: str | None = None
    # Shown above answers that did not come from the loaded documents
    notice: str | None = None
    # "documents" | "general" | "chat" | "emergency"
    answer_mode: str | None = None


class HealthResponse(BaseModel):
    status: str