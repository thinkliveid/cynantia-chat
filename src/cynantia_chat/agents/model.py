"""Helper model bersama untuk semua agent (OpenAI lewat LiteLLM)."""

from __future__ import annotations

import os

from google.adk.models.lite_llm import LiteLlm

from cynantia_chat.config import get_settings

_settings = get_settings()

# LiteLLM membaca kredensial dari environment.
if _settings.openai_api_key:
    os.environ.setdefault("OPENAI_API_KEY", _settings.openai_api_key)
if _settings.openai_base_url:
    os.environ.setdefault("OPENAI_API_BASE", _settings.openai_base_url)


def llm() -> LiteLlm:
    """Instance model OpenAI-compatible sesuai konfigurasi."""
    return LiteLlm(model=_settings.agent_model)
