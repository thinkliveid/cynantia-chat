"""Specialist Math — menghitung ekspresi aritmetika dengan aman.

Punya tool `calculate` sendiri (safe-eval pakai AST, bukan eval bawaan).
"""

from __future__ import annotations

import ast
import operator

from google.adk.agents import LlmAgent

from cynantia_chat.agents.model import llm

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


root_agent = LlmAgent(
    name="math_agent",
    model=llm(),
    description=(
        "Spesialis hitung-menghitung: menyelesaikan perhitungan aritmetika "
        "dan soal matematika numerik."
    ),
    instruction=(
        "Kamu spesialis matematika. Untuk perhitungan numerik, SELALU pakai "
        "tool calculate agar akurat, lalu jelaskan hasilnya singkat."
    ),
    tools=[calculate],
)
