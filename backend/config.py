"""Pydantic Settings — every runtime value comes from the environment.

No URLs, ports, or API keys are hardcoded. See ``.env.example``.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(
        default="postgresql+asyncpg://duebot:duebot@localhost:5432/duebot",
        description="SQLAlchemy async URL.",
    )
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    cors_origins: str = Field(default="http://localhost:3000")

    anthropic_api_key: str = Field(default="")
    anthropic_model: str = Field(default="claude-sonnet-4-20250514")

    gemini_api_key: str = Field(default="")
    gemini_model: str = Field(default="gemini-3-flash-preview")

    razorpay_key_id: str = Field(default="")
    razorpay_key_secret: str = Field(default="")
    razorpay_webhook_secret: str = Field(default="")

    whatsapp_mode: str = Field(default="simulated")
    whatsapp_api_token: str = Field(default="")
    whatsapp_phone_number_id: str = Field(default="")

    smtp_host: str = Field(default="")
    smtp_port: int = Field(default=587)
    smtp_username: str = Field(default="")
    smtp_password: str = Field(default="")
    smtp_from: str = Field(default="duebot@example.com")

    max_contacts_per_week: int = Field(default=3)
    confidence_threshold: float = Field(default=0.7)

    # Set ENABLE_POLLER=true to run the aging/nudge/promise cycle inside the
    # FastAPI process instead of as a separate `python -m backend.tasks.poller`.
    # Default off so tests and one-off scripts don't start background tasks.
    enable_poller: bool = Field(default=False)

    log_level: str = Field(default="INFO")

    @property
    def cors_origin_list(self) -> list[str]:
        """Split the comma-separated CORS allowlist."""
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def razorpay_configured(self) -> bool:
        """True when live test-mode Razorpay credentials are present."""
        return bool(self.razorpay_key_id and self.razorpay_key_secret)

    @property
    def anthropic_configured(self) -> bool:
        """True when a Claude API key is present."""
        return bool(self.anthropic_api_key)

    @property
    def gemini_configured(self) -> bool:
        """True when a Gemini API key is present."""
        return bool(self.gemini_api_key)


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings singleton."""
    return Settings()
