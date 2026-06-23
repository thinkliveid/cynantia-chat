"""Agent utama (orchestrator).

Tidak menjawab sendiri — tugasnya mengenali maksud pesan lalu MENDELEGASIKAN ke
specialist yang sesuai. Tiap specialist adalah A2A server terpisah yang diakses
lewat `RemoteA2aAgent` (lihat agents/specialists/*/server.py).

Menambah specialist baru: buat folder agent+server-nya, daftarkan URL di config,
lalu tambahkan satu `RemoteA2aAgent` ke daftar `sub_agents` di bawah.
"""

from __future__ import annotations

from google.adk.agents import LlmAgent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent

from cynantia_chat.agents.model import llm
from cynantia_chat.config import card_url, get_settings


def build_orchestrator() -> LlmAgent:
    settings = get_settings()

    faq_agent = RemoteA2aAgent(
        name="faq_agent",
        description=(
            "Spesialis FAQ: pertanyaan umum layanan, harga, jam operasional, "
            "kontak, kebijakan refund."
        ),
        agent_card=card_url(settings.faq_agent_url),
    )

    math_agent = RemoteA2aAgent(
        name="math_agent",
        description="Spesialis matematika: perhitungan aritmetika dan soal numerik.",
        agent_card=card_url(settings.math_agent_url),
    )

    return LlmAgent(
        name="orchestrator",
        model=llm(),
        description="Agent utama yang merutekan pesan ke specialist yang tepat.",
        instruction=(
            "Kamu adalah orchestrator Cynantia di Google Chat. Tugasmu MENGENALI "
            "maksud pesan pengguna lalu MENDELEGASIKAN ke sub-agent yang paling "
            "sesuai:\n"
            "- faq_agent: pertanyaan seputar layanan, harga, jam, kontak, refund.\n"
            "- math_agent: perhitungan atau soal matematika.\n\n"
            "Jangan menjawab teknis sendiri jika ada specialist yang lebih cocok — "
            "delegasikan. Untuk sapaan/obrolan ringan, kamu boleh menjawab singkat "
            "sendiri. Selalu pakai bahasa yang sama dengan pengguna."
        ),
        sub_agents=[faq_agent, math_agent],
    )
