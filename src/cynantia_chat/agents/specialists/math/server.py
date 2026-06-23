"""A2A server untuk specialist Math (session persisten di Postgres).

Jalankan: uvicorn cynantia_chat.agents.specialists.math.server:a2a_app --port 8003
"""

from __future__ import annotations

from cynantia_chat.agents.a2a import persistent_a2a_app
from cynantia_chat.agents.specialists.math.agent import root_agent
from cynantia_chat.config import get_settings

a2a_app = persistent_a2a_app(
    root_agent, port=get_settings().math_port, app_name="math_agent"
)
