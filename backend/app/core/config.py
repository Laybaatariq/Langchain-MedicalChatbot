from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- LLM Provider (keys come from .env only, never hardcode them) ---
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    groq_api_key: str = ""
    llm_model_name: str = "openai/gpt-oss-120b"
    llm_temperature: float = 0.1

    # --- Vector DB (Qdrant Cloud) ---
    qdrant_url: str = ""
    qdrant_api_key: str = ""
    qdrant_collection_name: str = "medical_docs"

    # --- Embeddings (fastembed, runs locally, no API key) ---
    embedding_model_name: str = "BAAI/bge-small-en-v1.5"
    embedding_dimension: int = 384

    # --- MongoDB Atlas ---
    mongodb_uri: str = ""
    mongodb_db_name: str = "medical_chatbot"
    mongodb_chat_collection: str = "chat_messages"

    # --- Safety layer ---
    triage_confidence_threshold: float = 0.6
    emergency_default_message: str = (
        "This sounds like it could be a medical emergency. "
        "Please contact your local emergency number or go to the "
        "nearest emergency room immediately."
    )

    # --- App settings ---
    app_env: str = "development"
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()