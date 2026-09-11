from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- LLM Provider ---
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    groq_api_key: str = ""
    llm_model_name: str = "llama-3.3-70b-versatile"
    llm_temperature: float = 0.1

    # --- Vector DB (Qdrant) ---
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    qdrant_collection_name: str = "medical_docs"

    # --- Embeddings ---
    embedding_model_name: str = "text-embedding-3-small"
    embedding_dimension: int = 1536

    # --- MongoDB ---
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db_name: str = "medical_chatbot_db"

    # --- Safety layer ---
    triage_confidence_threshold: float = 0.6
    emergency_default_message: str = (
        "This sounds like it could be a medical emergency. "
        "Please contact your local emergency number or go to the "
        "nearest emergency room immediately. I'm not able to help with "
        "emergencies directly."
    )

    # --- App settings ---
    app_env: str = "development"
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()