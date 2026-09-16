from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)


class SourceCitation(BaseModel):
    source: str
    score: float | None = None


class ChatResponse(BaseModel):
    answer: str
    category: str | None = None
    sources: list[SourceCitation] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str