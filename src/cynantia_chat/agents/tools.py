"""Registry tools untuk specialist.

Tool harus berupa fungsi Python (eksekutabel), jadi tidak bisa didefinisikan
hanya lewat Markdown. Daftarkan tool di sini, lalu rujuk NAMANYA dari frontmatter
`tools:` pada AGENT.md sebuah specialist.

Menambah tool baru:
  1. Tulis fungsinya (type hints + docstring jelas — dipakai LLM sebagai spec).
  2. Tambahkan ke dict TOOLS di bawah.
  3. Rujuk namanya di `tools:` pada AGENT.md specialist yang membutuhkan.
"""

from __future__ import annotations

import ast
import operator

# ---------------------------------------------------------------- FAQ ----

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


# --------------------------------------------------------------- Math ----

_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _eval(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.operand))
    raise ValueError("Ekspresi tidak didukung.")


def calculate(expression: str) -> dict:
    """Hitung ekspresi aritmetika, mis. "2*(3+4)/5".

    Args:
        expression: ekspresi aritmetika (+, -, *, /, //, %, **, kurung).

    Returns:
        dict berisi 'ok' (bool) dan 'result' atau 'error'.
    """
    try:
        tree = ast.parse(expression, mode="eval")
        return {"ok": True, "result": _eval(tree.body)}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


# ------------------------------------------------------------ Registry ----
# Tool BERSAMA yang bisa dipakai banyak agent — dirujuk lewat `tools:` di AGENT.md.
# Tool yang khusus milik satu skill TIDAK perlu di sini; cukup deklarasikan
# `tool.entrypoint` di SKILL.md-nya (auto-registrasi, lihat discovery.py).

TOOLS: dict[str, object] = {
    "lookup_faq": lookup_faq,
    "calculate": calculate,
}
