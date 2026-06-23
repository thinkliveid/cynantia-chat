"""Jembatan webhook -> orchestrator (multi-agent A2A), dengan STREAMING.

Webhook menjalankan ORCHESTRATOR di Runner-nya. Orchestrator mendelegasikan ke
specialist remote (RemoteA2aAgent) sesuai isi pesan.

Streaming: Runner dijalankan dengan StreamingMode.SSE sehingga `run_async` meng-
yield event parsial. `stream_agent` mengubahnya menjadi rangkaian SNAPSHOT teks
kumulatif (teks "sejauh ini") yang bisa dipakai untuk patch pesan Google Chat.

Persistensi: DatabaseSessionService (Postgres), session_id = nama thread Chat,
sehingga context per-thread bertahan lintas restart.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator

from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from google.genai import types

from cynantia_chat.agents.orchestrator import build_orchestrator
from cynantia_chat.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

APP_NAME = "cynantia-chat"

_session_service = DatabaseSessionService(db_url=settings.database_url)
_runner = Runner(
    app_name=APP_NAME,
    agent=build_orchestrator(),
    session_service=_session_service,
)


async def _ensure_session(session_id: str, user_id: str) -> None:
    session = await _session_service.get_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id
    )
    if session is None:
        await _session_service.create_session(
            app_name=APP_NAME, user_id=user_id, session_id=session_id
        )


async def stream_agent(
    text: str, *, session_id: str, user_id: str
) -> AsyncIterator[str]:
    """Yield snapshot teks kumulatif saat orchestrator/specialist menjawab.

    Tiap nilai yang di-yield adalah teks LENGKAP "sejauh ini" (bukan delta),
    sehingga konsumen tinggal mem-patch pesan Chat dengan nilai terbaru.
    """
    await _ensure_session(session_id, user_id)
    message = types.Content(role="user", parts=[types.Part(text=text)])
    run_config = RunConfig(streaming_mode=StreamingMode.SSE)

    accumulated = ""
    last_emitted = ""

    async for event in _runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=message,
        run_config=run_config,
    ):
        if not (event.content and event.content.parts):
            continue
        chunk = "".join(part.text for part in event.content.parts if part.text)
        if not chunk:
            continue

        if event.partial:
            # delta token -> tambahkan ke akumulasi
            accumulated += chunk
            if accumulated != last_emitted:
                last_emitted = accumulated
                yield accumulated
        elif event.is_final_response():
            # event final umumnya berisi teks lengkap (bukan delta)
            if chunk != last_emitted:
                last_emitted = chunk
                yield chunk


async def ask_agent(text: str, *, session_id: str, user_id: str) -> str:
    """Versi non-streaming (sekali jawab) — fallback bila diperlukan."""
    final = ""
    async for snapshot in stream_agent(text, session_id=session_id, user_id=user_id):
        final = snapshot
    return final or "Maaf, aku belum bisa menjawab itu sekarang."
