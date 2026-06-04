"""Application settings loaded from environment / .env file."""
from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
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
    cors_origins: List[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )

    # STT
    stt_provider: str = "mock"  # mock | openrouter | future_local
    script_loop_sec: int = 52

    # OpenRouter
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "mistralai/mistral-7b-instruct:free"
    openrouter_timeout_s: float = 4.0

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors(cls, v):
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

    @field_validator("stt_provider")
    @classmethod
    def _validate_provider(cls, v: str) -> str:
        allowed = {"mock", "openrouter", "future_local"}
        v_lower = v.lower().strip()
        if v_lower not in allowed:
            raise ValueError(f"stt_provider must be one of {allowed}, got {v!r}")
        return v_lower


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
