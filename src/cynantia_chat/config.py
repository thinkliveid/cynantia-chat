"""Konfigurasi terpusat (dibaca dari environment / file .env)."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

WELL_KNOWN_CARD = "/.well-known/agent-card.json"


def card_url(base_url: str) -> str:
    """URL agent card A2A dari base URL sebuah agent server."""
    return f"{base_url.rstrip('/')}{WELL_KNOWN_CARD}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- Model (OpenAI / OpenAI-compatible), dipakai semua agent ---
    openai_api_key: str = ""
    agent_model: str = "openai/gpt-4o-mini"
    openai_base_url: str = "https://api.openai.com/v1"

    # --- Persistensi (Postgres) untuk session/memory orchestrator ---
    # SQLAlchemy URL. Driver psycopg dipakai untuk Postgres.
    database_url: str = "postgresql+psycopg://cynantia:cynantia@postgres:5432/cynantia"

    # --- Registry specialist (tiap satu A2A server sendiri) ---
    # Base URL dilihat dari orchestrator (di compose = nama service).
    faq_agent_url: str = "http://faq:8002"
    math_agent_url: str = "http://math:8003"
    # Port tempat tiap specialist listen di dalam containernya.
    faq_port: int = 8002
    math_port: int = 8003

    # --- Webhook backend ---
    webhook_host: str = "0.0.0.0"
    webhook_port: int = 8080

    # --- Google Chat ---
    google_service_account_file: str = "/secrets/service-account.json"
    chat_audience: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
