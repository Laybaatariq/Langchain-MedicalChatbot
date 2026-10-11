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


class QuickReplies(BaseModel):
    """Buttons shown under a question. mode: single | multi | text."""
    mode: str
    options: list[str] = Field(default_factory=list)
    skip_label: str | None = None
    confirm_label: str | None = None  # only for mode "multi"


class Progress(BaseModel):
    current: int
    total: int
    label: str


class DoctorCard(BaseModel):
    id: str
    name: str
    specialty: str
    city: str
    experience_years: int
    fee_pkr: int
    modes: list[str] = Field(default_factory=list)
    days: list[str] = Field(default_factory=list)
    is_sample: bool = True


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    category: str | None = None
    sources: list[SourceCitation] = Field(default_factory=list)
    disclaimer: str | None = None
    # Shown above answers that did not come from the loaded documents
    notice: str | None = None
    # "documents" | "general" | "chat" | "emergency" | "intake"
    answer_mode: str | None = None
    # Symptom intake
    quick_replies: QuickReplies | None = None
    progress: Progress | None = None
    doctors: list[DoctorCard] = Field(default_factory=list)
    urgency: str | None = None  # "urgent" | "routine" | "self_care"
    urgency_label: str | None = None


class HealthResponse(BaseModel):
    status: str