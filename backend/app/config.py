"""Application configuration loaded from environment variables.

Uses pydantic-settings to validate and parse env vars (from a .env file
locally). Required settings with no default will cause a startup crash if
missing — this is intentional.
"""

import json
from typing import Any
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the backend.

    All tunables are defined here and loaded from environment variables.
    A `.env` file in ``backend/`` is read automatically during local
    development.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── NVIDIA inference API ────────────────────────────────────────────
    nvidia_api_key: str  # required — no default
    nvidia_api_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_model: str = "meta/llama-3.1-8b-instruct"
    available_models: str | list[str] = [
        "nvidia/nemotron-3-ultra-550b-a55b",
        "meta/llama-3.3-70b-instruct",
        "deepseek-ai/deepseek-v4-flash",
        "deepseek-ai/deepseek-v4-pro",
    ]
    nvidia_temperature: float = 0.7
    nvidia_max_tokens: int = 1024
    nvidia_request_timeout_seconds: int = 60

    # ── Database ────────────────────────────────────────────────────────
    database_url: str  # required — async driver, e.g. postgresql+asyncpg://...

    # ── CORS ────────────────────────────────────────────────────────────
    cors_allowed_origins: str | list[str] = [
        "http://localhost:8000",
        "http://127.0.0.1:5500",
    ]

    @field_validator("cors_allowed_origins", "available_models", mode="before")
    @classmethod
    def assemble_list_origins(cls, v: Any) -> list[str] | Any:
        if isinstance(v, str):
            v_str = v.strip()
            if not v_str:
                return []
            if v_str.startswith("[") and v_str.endswith("]"):
                try:
                    return json.loads(v_str)
                except Exception:
                    v_str = v_str[1:-1].strip()
            return [i.strip(" '\"`") for i in v_str.split(",") if i.strip(" '\"`")]
        return v

    # ── General ─────────────────────────────────────────────────────────
    environment: str = "development"


settings = Settings()  # type: ignore[call-arg]

