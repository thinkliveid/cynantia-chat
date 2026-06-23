"""Webhook FastAPI yang menerima event Google Chat dan membalas di thread.

Alur:
  1. Google Chat POST event ke /  (saat app di-mention di space/thread, atau DM).
  2. Kita verifikasi token (opsional) lalu ACK 200 cepat.
  3. Di background: tanya agent A2A -> post jawaban ke thread yang sama via Chat API.

Catatan mention:
  - Di SPACE (ROOM), Google Chat hanya mengirim event saat app DI-MENTION.
  - `message.argumentText` = teks tanpa mention app (kalau ada), lebih bersih.
  - `message.thread.name` = thread tempat balasan harus masuk.
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import BackgroundTasks, FastAPI, Header, Request, Response

from cynantia_chat.chat.agent_client import stream_agent
from cynantia_chat.chat.chat_client import (
    create_message_in_thread,
    post_reply_in_thread,
    update_message,
)
from cynantia_chat.config import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cynantia.webhook")
settings = get_settings()

app = FastAPI(title="Cynantia Chat Webhook")

# Issuer token untuk request yang berasal dari Google Chat.
_CHAT_ISSUER = "chat@system.gserviceaccount.com"

# Jeda minimum antar patch agar tidak kena rate limit Chat API (detik).
_MIN_PATCH_INTERVAL = 1.0


def _verify_chat_token(authorization: str | None) -> bool:
    """Verifikasi bahwa request benar-benar dari Google Chat.

    Dilewati jika `chat_audience` kosong (mode dev). Untuk produksi, set
    CHAT_AUDIENCE = project number GCP.
    """
    if not settings.chat_audience:
        return True
    if not authorization or not authorization.startswith("Bearer "):
        return False

    token = authorization.split(" ", 1)[1]
    try:
        from google.auth.transport import requests as g_requests
        from google.oauth2 import id_token

        claims = id_token.verify_token(
            token, g_requests.Request(), audience=settings.chat_audience
        )
        return claims.get("iss") == _CHAT_ISSUER and claims.get("email") == _CHAT_ISSUER
    except Exception as exc:  # noqa: BLE001
        logger.warning("Verifikasi token gagal: %s", exc)
        return False


async def _handle_message(text: str, space_name: str, thread_name: str, user_id: str) -> None:
    """Tugas background: stream jawaban agent ke thread (create + patch)."""
    loop = asyncio.get_event_loop()
    message_name: str | None = None
    last_text = ""
    latest = ""
    last_patch = 0.0

    try:
        # session_id = thread => agent mengingat konteks per-thread.
        async for snapshot in stream_agent(text, session_id=thread_name, user_id=user_id):
            if not snapshot:
                continue
            latest = snapshot

            if message_name is None:
                # Snapshot pertama -> buat pesan di thread.
                message_name = await asyncio.to_thread(
                    create_message_in_thread, space_name, thread_name, snapshot
                )
                last_text, last_patch = snapshot, loop.time()
                continue

            # Throttle patch supaya aman dari rate limit.
            now = loop.time()
            if snapshot != last_text and (now - last_patch) >= _MIN_PATCH_INTERVAL:
                await asyncio.to_thread(update_message, message_name, snapshot)
                last_text, last_patch = snapshot, now

        # Pastikan teks final ter-patch (snapshot terakhir mungkin ter-throttle).
        if message_name is not None and latest and latest != last_text:
            await asyncio.to_thread(update_message, message_name, latest)

        # Tidak ada output sama sekali.
        if message_name is None:
            await asyncio.to_thread(
                post_reply_in_thread,
                space_name,
                thread_name,
                "Maaf, aku belum bisa menjawab itu sekarang.",
            )
    except Exception:  # noqa: BLE001
        logger.exception("Gagal memproses pesan di thread %s", thread_name)
        err = "Maaf, terjadi kendala saat memproses pesanmu."
        try:
            if message_name is not None:
                await asyncio.to_thread(update_message, message_name, err)
            else:
                await asyncio.to_thread(
                    post_reply_in_thread, space_name, thread_name, err
                )
        except Exception:  # noqa: BLE001
            logger.exception("Gagal mengirim pesan error fallback.")


@app.get("/healthz")
async def healthz() -> dict:
    return {"status": "ok"}


@app.post("/")
async def on_event(
    request: Request,
    background: BackgroundTasks,
    authorization: str | None = Header(default=None),
) -> Response | dict:
    if not _verify_chat_token(authorization):
        return Response(status_code=401, content="invalid token")

    event = await request.json()
    event_type = event.get("type")

    # Sapaan saat app ditambahkan ke space.
    if event_type == "ADDED_TO_SPACE":
        return {"text": "Halo! Mention aku (@Cynantia) kapan saja untuk bertanya. 👋"}

    if event_type != "MESSAGE":
        # ADDED/REMOVED/lain — cukup ACK.
        return Response(status_code=200)

    message = event.get("message", {})
    space = event.get("space", {})
    user = event.get("user", {})

    space_name = space.get("name", "")
    thread_name = message.get("thread", {}).get("name", "")
    user_id = user.get("name", "user")

    # argumentText = teks tanpa mention app; fallback ke text mentah.
    text = (message.get("argumentText") or message.get("text") or "").strip()

    if not text or not thread_name:
        logger.info("Event MESSAGE tanpa teks/thread, diabaikan.")
        return Response(status_code=200)

    # ACK cepat; jawaban dikirim async ke thread yang sama.
    background.add_task(_handle_message, text, space_name, thread_name, user_id)
    return Response(status_code=200)
