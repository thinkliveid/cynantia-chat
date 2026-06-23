"""Konfigurasi terpusat (dibaca dari environment / file .env)."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- Model (OpenAI / OpenAI-compatible), dipakai semua agent ---
    openai_api_key: str = ""
    agent_model: str = "openai/gpt-4o-mini"
    openai_base_url: str = "https://api.openai.com/v1"

    # --- Folder konfigurasi agent (AGENT.md / MEMORY.md / skills/ per agent) ---
    # Relatif terhadap working directory. Di Docker = /app/agents_config.
    agents_config_dir: str = "agents_config"

    # --- Persistensi (Postgres) untuk session/memory ---
    # SQLAlchemy URL. Driver psycopg dipakai untuk Postgres.
    database_url: str = "postgresql+psycopg://cynantia:cynantia@postgres:5432/cynantia"

    # --- Webhook backend ---
    webhook_host: str = "0.0.0.0"
    webhook_port: int = 8080

    # --- Google Chat ---
    google_service_account_file: str = "/secrets/service-account.json"
    chat_audience: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
