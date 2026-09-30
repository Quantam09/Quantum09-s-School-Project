"""Application settings (loaded from environment / services/api/.env)."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "local"
    auto_create_tables: bool = True

    database_url: str = "postgresql+psycopg://lar:lar_secret@localhost:5432/lar"

    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 120

    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    # Cross-module adapters until the real modules are merged:
    #   coin: "stub" (local demo) | "internal" (Developer C's CoinService)
    #   rag:  "stub" (local demo)  | "internal" (Developer A's POST /api/v1/rag/search)
    coin_mode: str = "stub"
    rag_mode: str = "stub"
    rag_search_url: str = ""

    # Mission A (Developer A scope): resource layer + voice AI
    storage_mode: str = "local"  # local | s3
    data_dir: str = "./data"  # local file storage root
    s3_endpoint_url: str = ""  # e.g. http://minio:9000 in compose
    s3_bucket: str = "lar-resources"
    max_upload_mb: int = 25
    allowed_upload_types: str = (
        "audio/wav,audio/x-wav,audio/mpeg,audio/mp3,audio/mp4,audio/m4a,audio/ogg,"
        "audio/webm,text/plain,text/markdown"
    )
    queue_mode: str = "inline"  # inline (background threads) | rq (Redis + RQ worker)
    redis_url: str = "redis://localhost:6379/0"
    asr_mode: str = "real"  # real (faster-whisper) | mock
    asr_model_size: str = "small"  # tiny | base | small | medium
    tts_mode: str = "stub"  # stub (README fallback for Luxembourgish) | real
    embeddings_mode: str = "real"  # real (fastembed e5-small) | mock
    embedding_dim: int = 384
    vector_search_url: str = ""  # optional external vector service; unused by default

    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def allowed_upload_type_list(self) -> list[str]:
        return [t.strip() for t in self.allowed_upload_types.split(",") if t.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
