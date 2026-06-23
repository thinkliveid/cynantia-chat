"""Helper untuk meng-expose specialist sebagai A2A server DENGAN session persisten.

`to_a2a()` ADK menerima parameter `runner=`, sehingga kita bisa menyuntik Runner
ber-`DatabaseSessionService` (Postgres) alih-alih service in-memory default.
Dengan begitu, setiap specialist MENGINGAT percakapan di sesinya secara persisten
(bertahan lintas restart), terisolasi per `app_name`.

Catatan:
  - Yang dipersisten adalah SESSION (state percakapan per sesi). ADK belum punya
    long-term memory service berbasis SQL bawaan; memory_service tetap in-memory
    (untuk long-term lintas-sesi yang persisten, opsi bawaan saat ini Vertex).
  - session_id di sisi specialist ditentukan ADK dari contextId A2A saat dipanggil
    orchestrator, sehingga kontinuitas mengikuti konteks pemanggilan.
"""

from __future__ import annotations

from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.adk.agents import BaseAgent
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from starlette.applications import Starlette

from cynantia_chat.config import get_settings


def persistent_a2a_app(agent: BaseAgent, *, port: int, app_name: str) -> Starlette:
    """Bangun ASGI app A2A untuk `agent` dengan session persisten di Postgres."""
    settings = get_settings()
    runner = Runner(
        app_name=app_name,
        agent=agent,
        session_service=DatabaseSessionService(db_url=settings.database_url),
    )
    return to_a2a(agent, port=port, runner=runner)
