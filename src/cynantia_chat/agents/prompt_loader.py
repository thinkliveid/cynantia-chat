"""Loader konfigurasi agent dari Markdown + skills berformat Agent Skills.

Tiap agent punya folder di `agents_config/<nama>/`:
  - AGENT.md   : peran & instruksi utama (WAJIB). Boleh diawali frontmatter YAML:
                 ---
                 description: ringkasan untuk routing orchestrator
                 tools: [nama_tool, ...]   # opsional, di-resolve dari registry tools
                 ---
  - MEMORY.md  : pengetahuan/fakta tetap (opsional)
  - skills/    : satu subfolder per skill, mengikuti standar Agent Skills
                 (https://agentskills.io). Tiap skill = folder berisi SKILL.md
                 dengan frontmatter `name` + `description` (wajib).

Body AGENT.md + MEMORY.md + ringkasan setiap skill digabung jadi instruction.
Skill berformat standar bersifat portabel & bisa divalidasi `skills-ref validate`.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from cynantia_chat.config import get_settings

logger = logging.getLogger(__name__)

# name skill yang valid menurut spec: lowercase a-z 0-9 dan hyphen, tanpa
# hyphen di awal/akhir, tanpa hyphen berurutan, maks 64 char.
_SKILL_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


@dataclass
class Skill:
    name: str
    description: str
    instructions: str
    directory: Path
    # "scripts/file.py:fungsi" — fungsi tool self-contained yang auto-didaftarkan.
    tool_entrypoint: str | None = None


@dataclass
class AgentConfig:
    name: str
    description: str
    instruction: str
    tools: list[str] = field(default_factory=list)
    skills: list[Skill] = field(default_factory=list)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip() if path.exists() else ""


def _safe_name(name: str) -> str:
    return re.sub(r"\W+", "_", name).strip("_").lower() or "agent"


def _split_frontmatter(raw: str) -> tuple[dict, str]:
    """Pisahkan frontmatter YAML (opsional) dari body Markdown."""
    if raw.startswith("---"):
        parts = raw.split("\n", 1)
        if len(parts) == 2:
            rest = parts[1]
            end = rest.find("\n---")
            if end != -1:
                try:
                    meta = yaml.safe_load(rest[:end]) or {}
                except yaml.YAMLError:
                    meta = {}
                if isinstance(meta, dict):
                    return meta, rest[end + 4 :].lstrip("\n")
    return {}, raw


def _load_skills(base: Path) -> list[Skill]:
    """Temukan skill berformat Agent Skills di `<base>/skills/<nama>/SKILL.md`."""
    skills_dir = base / "skills"
    if not skills_dir.is_dir():
        return []

    skills: list[Skill] = []
    for folder in sorted(p for p in skills_dir.iterdir() if p.is_dir()):
        skill_md = folder / "SKILL.md"
        if not skill_md.exists():
            continue

        meta, body = _split_frontmatter(_read(skill_md))
        name = str(meta.get("name") or folder.name)
        description = str(meta.get("description") or "")

        # Validasi ringan sesuai spec (peringatan, tidak gagal).
        if name != folder.name:
            logger.warning(
                "Skill '%s': field name '%s' tidak sama dengan nama folder.",
                folder.name,
                name,
            )
        if not _SKILL_NAME_RE.match(name) or len(name) > 64:
            logger.warning("Skill '%s': name tidak sesuai format Agent Skills.", name)
        if not description:
            logger.warning("Skill '%s': description wajib dan tidak boleh kosong.", name)

        # Frontmatter `tool.entrypoint` (opsional) untuk auto-registrasi tool.
        tool_meta = meta.get("tool")
        entrypoint = None
        if isinstance(tool_meta, dict):
            entrypoint = tool_meta.get("entrypoint")
        elif isinstance(tool_meta, str):
            entrypoint = tool_meta
        entrypoint = str(entrypoint) if entrypoint else None

        skills.append(
            Skill(
                name=name,
                description=description,
                instructions=body,
                directory=folder,
                tool_entrypoint=entrypoint,
            )
        )

    return skills


def load_agent_config(agent_name: str) -> AgentConfig:
    """Baca AGENT.md (+ MEMORY.md + skills/) jadi AgentConfig."""
    base = Path(get_settings().agents_config_dir) / agent_name

    raw = _read(base / "AGENT.md")
    if not raw:
        raise FileNotFoundError(
            f"AGENT.md wajib ada untuk agent '{agent_name}' di folder {base}/"
        )

    meta, body = _split_frontmatter(raw)
    sections = [body]

    memory_md = _read(base / "MEMORY.md")
    if memory_md:
        sections.append("# Pengetahuan tetap (MEMORY.md)\n\n" + memory_md)

    skills = _load_skills(base)
    if skills:
        blocks = ["# Skills (Agent Skills)\n"]
        for s in skills:
            blocks.append(f"## {s.name}\n\n{s.description}\n\n{s.instructions}".strip())
        sections.append("\n\n".join(blocks))

    tools = meta.get("tools") or []
    if isinstance(tools, str):
        tools = [tools]

    return AgentConfig(
        name=_safe_name(agent_name),
        description=str(meta.get("description") or f"Specialist {agent_name}"),
        instruction="\n\n".join(sections),
        tools=[str(t) for t in tools],
        skills=skills,
    )
