#!/usr/bin/env python3
"""Hitung penawaran harga. Bisa dijalankan langsung (CLI) atau diimpor.

CLI:
    python quote.py --package pro --qty 5 --term 12

Sebagai modul:
    from quote import compute_quote
    compute_quote("pro", 5, 12, price_list)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def term_discount(term_months: int) -> float:
    if term_months >= 12:
        return 0.20
    if term_months >= 6:
        return 0.10
    return 0.0


def volume_discount(quantity: int) -> float:
    if quantity >= 10:
        return 0.10
    if quantity >= 5:
        return 0.05
    return 0.0


def compute_quote(
    package: str, quantity: int, term_months: int, price_list: dict
) -> dict:
    """Hitung penawaran. `price_list` = isi assets/price-list.json."""
    packages = price_list.get("packages", {})
    currency = price_list.get("currency", "IDR")

    base = packages.get(str(package).lower())
    if base is None:
        return {
            "ok": False,
            "error": f"Paket tidak dikenal: {package}",
            "available_packages": sorted(packages),
        }

    quantity = max(1, int(quantity))
    term_months = max(1, int(term_months))
    td = term_discount(term_months)
    vd = volume_discount(quantity)

    monthly_gross = base * quantity
    monthly_net = monthly_gross * (1 - td) * (1 - vd)
    contract_total = monthly_net * term_months

    return {
        "ok": True,
        "currency": currency,
        "package": str(package).lower(),
        "quantity": quantity,
        "term_months": term_months,
        "unit_price": base,
        "term_discount_pct": round(td * 100),
        "volume_discount_pct": round(vd * 100),
        "monthly_gross": round(monthly_gross),
        "monthly_net": round(monthly_net),
        "contract_total": round(contract_total),
    }


def _load_price_list() -> dict:
    path = Path(__file__).resolve().parent.parent / "assets" / "price-list.json"
    return json.loads(path.read_text(encoding="utf-8"))


def price_quote(package: str, quantity: int, term_months: int) -> dict:
    """Buat penawaran harga untuk sebuah paket langganan.

    Fungsi tool self-contained: memuat data harganya sendiri dari
    assets/price-list.json, jadi bisa di-auto-register lewat SKILL.md
    (`tool.entrypoint`) tanpa perlu kode di tools.py.

    Args:
        package: nama paket (basic | pro | enterprise).
        quantity: jumlah lisensi.
        term_months: durasi kontrak dalam bulan.

    Returns:
        dict rincian penawaran (lihat compute_quote).
    """
    return compute_quote(package, int(quantity), int(term_months), _load_price_list())


def main() -> None:
    parser = argparse.ArgumentParser(description="Hitung penawaran harga.")
    parser.add_argument("--package", required=True, help="basic | pro | enterprise")
    parser.add_argument("--qty", type=int, required=True, help="jumlah lisensi")
    parser.add_argument("--term", type=int, required=True, help="durasi (bulan)")
    args = parser.parse_args()

    result = compute_quote(args.package, args.qty, args.term, _load_price_list())
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
