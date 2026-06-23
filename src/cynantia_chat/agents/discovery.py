"""Auto-discovery specialist + auto-registrasi tool dari folder `agents_config/`.

Setiap subfolder (kecuali `orchestrator`) yang berisi AGENT.md otomatis menjadi
satu specialist LlmAgent in-process. Tambah specialist = buat folder + restart.

Tool sebuah specialist berasal dari dua sumber, lalu digabung:
  1. Registry bersama (tools.py) — dirujuk lewat `tools:` di frontmatter AGENT.md.
  2. Auto-registrasi dari skill — bila SKILL.md punya `tool.entrypoint`
     ("scripts/file.py:fungsi"), fungsi itu di-import dan didaftarkan otomatis,
     TANPA menyentuh tools.py.

Catatan: auto-registrasi meng-import script dari agents_config/ saat startup —
aman selama folder config setara-tepercaya dengan kode (operator yang sama).
"""

from __future__ import annotations

import importlib.util
import logging
from pathlib import Path

from google.adk.agents import LlmAgent

from cynantia_chat.agents.model import llm
from cynantia_chat.agents.prompt_loader import Skill, load_agent_config
from cynantia_chat.agents.tools import TOOLS
from cynantia_chat.config import get_settings

logger = logging.getLogger(__name__)

# Folder yang BUKAN specialist.
_RESERVED = {"orchestrator"}


def _load_skill_tool(skill: Skill):
    """Import fungsi tool dari `skill.tool_entrypoint`, mis. 'scripts/q.py:fn'."""
    if not skill.tool_entrypoint:
        return None
    rel, _, func_name = skill.tool_entrypoint.partition(":")
    if not func_name:
        logger.warning(
            "Skill '%s': tool.entrypoint harus berformat 'path.py:fungsi'.", skill.name
        )
        return None

    script = (skill.directory / rel).resolve()
    if not script.exists():
        logger.warning("Skill '%s': script tool tidak ditemukan: %s", skill.name, script)
        return None

    spec = importlib.util.spec_from_file_location(f"skill_tool_{skill.name}", script)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    fn = getattr(module, func_name, None)
    if not callable(fn):
        logger.warning(
            "Skill '%s': fungsi '%s' tak ditemukan di %s.", skill.name, func_name, script
        )
        return None
    return fn


def _collect_tools(cfg) -> list:
    """Gabungkan tool registry (AGENT.md) + tool auto dari skill."""
    tools: list = []
    seen: set[str] = set()

    def add(fn) -> None:
        key = getattr(fn, "__name__", str(fn))
        if key not in seen:
            seen.add(key)
            tools.append(fn)

    # 1. Tool registry yang dirujuk di AGENT.md.
    for name in cfg.tools:
        if name in TOOLS:
            add(TOOLS[name])
        else:
            logger.warning(
                "Agent '%s' merujuk tool tak terdaftar: %s (lihat tools.py)",
                cfg.name,
                name,
            )

    # 2. Tool yang dideklarasikan skill lewat tool.entrypoint.
    for skill in cfg.skills:
        fn = _load_skill_tool(skill)
        if fn is not None:
            add(fn)

    return tools


def discover_specialists() -> list[LlmAgent]:
    """Pindai folder konfigurasi dan bangun semua specialist in-process."""
    base = Path(get_settings().agents_config_dir)
    if not base.is_dir():
        logger.warning("Folder konfigurasi agent tidak ditemukan: %s", base)
        return []

    specialists: list[LlmAgent] = []
    for folder in sorted(p for p in base.iterdir() if p.is_dir()):
        if folder.name in _RESERVED or folder.name.startswith("."):
            continue
        if not (folder / "AGENT.md").exists():
            continue

        cfg = load_agent_config(folder.name)
        tools = _collect_tools(cfg)

        specialists.append(
            LlmAgent(
                name=cfg.name,
                model=llm(),
                description=cfg.description,
                instruction=cfg.instruction,
                tools=tools,
            )
        )
        logger.info(
            "Specialist '%s' dimuat (%d tool, %d skill)",
            cfg.name,
            len(tools),
            len(cfg.skills),
        )

    return specialists
