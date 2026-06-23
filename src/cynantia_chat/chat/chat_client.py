"""Klien Google Chat API untuk membalas ke dalam thread, termasuk STREAMING.

Google Chat tidak punya streaming token native. Efek "mengetik" disimulasikan:
  1. create  -> kirim potongan teks pertama (mengembalikan message.name)
  2. patch   -> update teks message yang sama berulang kali (updateMask=text)

Balasan masuk thread yang sama lewat:
  thread = {"name": <thread.name dari event>} +
  messageReplyOption = "REPLY_MESSAGE_FALLBACK_TO_NEW_THREAD"
"""

from __future__ import annotations

import logging
from functools import lru_cache

from google.oauth2 import service_account
from googleapiclient.discovery import build

from cynantia_chat.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_SCOPES = ["https://www.googleapis.com/auth/chat.bot"]


@lru_cache
def _chat_service():
    creds = service_account.Credentials.from_service_account_file(
        settings.google_service_account_file, scopes=_SCOPES
    )
    return build("chat", "v1", credentials=creds, cache_discovery=False)


def create_message_in_thread(space_name: str, thread_name: str, text: str) -> str:
    """Buat pesan baru di thread `thread_name`. Kembalikan message.name."""
    result = (
        _chat_service()
        .spaces()
        .messages()
        .create(
            parent=space_name,
            body={"text": text, "thread": {"name": thread_name}},
            messageReplyOption="REPLY_MESSAGE_FALLBACK_TO_NEW_THREAD",
        )
        .execute()
    )
    return result["name"]  # "spaces/AAA/messages/BBB"


def update_message(message_name: str, text: str) -> None:
    """Update teks pesan yang sudah ada (untuk efek streaming)."""
    (
        _chat_service()
        .spaces()
        .messages()
        .patch(name=message_name, updateMask="text", body={"text": text})
        .execute()
    )


def post_reply_in_thread(space_name: str, thread_name: str, text: str) -> dict:
    """Kirim satu pesan utuh ke thread (dipakai untuk fallback/error)."""
    result = (
        _chat_service()
        .spaces()
        .messages()
        .create(
            parent=space_name,
            body={"text": text, "thread": {"name": thread_name}},
            messageReplyOption="REPLY_MESSAGE_FALLBACK_TO_NEW_THREAD",
        )
        .execute()
    )
    logger.info("Balasan terkirim ke thread %s", thread_name)
    return result
