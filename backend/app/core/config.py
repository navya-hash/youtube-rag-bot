
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "YouTube RAG Bot API"
    app_env: str = "development"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    redis_url: str
    openai_api_key: str | None = None
    qdrant_url: str | None = None
    qdrant_api_key: str | None = None
    qdrant_collection_name: str = "youtube_transcripts_multilingual"
    qdrant_multilingual_collection_name: str = "youtube_transcripts_multilingual"
    groq_api_key: str | None = None
    groq_model: str = "openai/gpt-oss-120b" 
    groq_classifier_model: str = "openai/gpt-oss-20b" 
    # embedding_model: str = "text-embedding-3-small"
    # embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_model: str = (
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )
    embedding_dimension: int = 384
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def allowed_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()


# BaseSettings reads configuration from environment variables and .env.

# allowed_origins converts a comma-separated string into a Python list for CORS.

# @lru_cache avoids repeatedly creating the same settings object.

# extra="ignore" allows unrelated environment variables without breaking configuration loading.