from fastapi import APIRouter
from app.api.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Simple endpoint to verify the server is up and running."""
    return HealthResponse()