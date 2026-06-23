"""Specialist FAQ — menjawab pertanyaan umum/seputar produk.

Punya tool sendiri (`lookup_faq`) dan instruction sendiri. Ini contoh; ganti
sumber data FAQ dengan basis pengetahuan/RAG sungguhan sesuai kebutuhan.
"""

from __future__ import annotations

from google.adk.agents import LlmAgent

from cynantia_chat.agents.model import llm

# Sumber FAQ sederhana (ganti dengan DB/RAG).
_FAQ: dict[str, str] = {
    "jam operasional": "Layanan kami buka Senin–Jumat, 09.00–17.00 WIB.",
    "kontak": "Hubungi kami di support@cynantia.example atau +62-21-000-0000.",
    "harga": "Paket mulai Rp99.000/bulan. Detail di cynantia.example/harga.",
    "refund": "Refund penuh dalam 14 hari pertama tanpa syarat.",
}


def lookup_faq(topic: str) -> dict:
    """Cari jawaban FAQ untuk sebuah topik.

    Args:
        topic: kata kunci topik, mis. "harga", "refund", "jam operasional".

    Returns:
        dict berisi 'found' (bool) dan 'answer' (str).
    """
    key = topic.lower().strip()
    for k, v in _FAQ.items():
        if k in key or key in k:
            return {"found": True, "answer": v}
    return {
        "found": False,
        "answer": "Topik tidak ditemukan di FAQ.",
        "available_topics": list(_FAQ.keys()),
    }


root_agent = LlmAgent(
    name="faq_agent",
    model=llm(),
    description=(
        "Spesialis FAQ: menjawab pertanyaan umum seputar layanan, harga, "
        "jam operasional, kontak, dan kebijakan refund."
    ),
    instruction=(
        "Kamu spesialis FAQ Cynantia. Gunakan tool lookup_faq untuk mencari "
        "jawaban resmi sebelum menjawab. Jika tidak ada di FAQ, katakan jujur "
        "dan sarankan menghubungi support. Jawab singkat dan ramah."
    ),
    tools=[lookup_faq],
)
