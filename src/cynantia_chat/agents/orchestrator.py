"""Agent utama (orchestrator), in-process dengan specialist auto-discovered.

Tidak menjawab teknis sendiri — mengenali maksud pesan lalu MENDELEGASIKAN ke
specialist. Specialist ditemukan otomatis dari folder `agents_config/` (lihat
discovery.py), sehingga menambah specialist cukup dengan membuat folder + restart.

Daftar specialist yang tersedia disuntikkan otomatis ke instruksi orchestrator
agar ia tahu ke mana harus mendelegasikan tanpa perlu edit manual.
"""

from __future__ import annotations

from google.adk.agents import LlmAgent

from cynantia_chat.agents.discovery import discover_specialists
from cynantia_chat.agents.model import llm
from cynantia_chat.agents.prompt_loader import load_agent_config


def build_orchestrator() -> LlmAgent:
    specialists = discover_specialists()
    cfg = load_agent_config("orchestrator")

    roster = "\n".join(f"- {s.name}: {s.description}" for s in specialists)
    instruction = cfg.instruction
    if roster:
        instruction += (
            "\n\n# Specialist yang tersedia (otomatis)\n\n"
            + roster
            + "\n\nDelegasikan ke salah satu specialist di atas sesuai maksud "
            "pengguna. Untuk sapaan/obrolan ringan, jawab singkat sendiri."
        )

    return LlmAgent(
        name="orchestrator",
        model=llm(),
        description=cfg.description,
        instruction=instruction,
        sub_agents=specialists,
    )
