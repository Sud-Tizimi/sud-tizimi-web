"""Application settings loaded from environment / .env file."""
from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    # Stored as a raw string — pydantic-settings 2.6.1 expects JSON for List
    # fields out of .env, which is brittle. We split on comma in
    # ``cors_origins_list`` and fall back to sensible defaults.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # STT (Phase A — unchanged from CP1)
    stt_provider: str = "mock"  # mock | openrouter | future_local
    script_loop_sec: int = 52

    # OpenRouter
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "mistralai/mistral-7b-instruct:free"
    openrouter_timeout_s: float = 4.0

    # ----- Phase A additions -----

    # MySQL (async via aiomysql). Default expects a local server.
    database_url: str = "mysql+aiomysql://sud:sud@127.0.0.1:3306/sudtizimi?charset=utf8mb4"

    # JWT
    jwt_secret: str = "change-me-in-prod-use-a-long-random-string"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24  # 24 hours

    # File storage (Phase B uses this; defined now so the config surface is stable)
    storage_root: str = "uploads"
    max_upload_bytes: int = 25 * 1024 * 1024  # 25 MB
    allowed_upload_extensions: str = "pdf,docx,jpg,jpeg,png"

    @field_validator("stt_provider")
    @classmethod
    def _validate_provider(cls, v: str) -> str:
        allowed = {"mock", "openrouter", "future_local"}
        v_lower = v.lower().strip()
        if v_lower not in allowed:
            raise ValueError(f"stt_provider must be one of {allowed}, got {v!r}")
        return v_lower

    @field_validator("database_url")
    @classmethod
    def _validate_database_url(cls, v: str) -> str:
        v_stripped = v.strip()
        if not v_stripped:
            raise ValueError("database_url is required (Phase A requires MySQL)")
        if v_stripped.startswith("sqlite"):
            raise ValueError(
                "sqlite is not allowed in Phase A — set DATABASE_URL to mysql+aiomysql://…"
            )
        return v_stripped

    @property
    def cors_origins_list(self) -> List[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def allowed_upload_extensions_tuple(self) -> tuple[str, ...]:
        return tuple(
            ext.strip().lower()
            for ext in self.allowed_upload_extensions.split(",")
            if ext.strip()
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
