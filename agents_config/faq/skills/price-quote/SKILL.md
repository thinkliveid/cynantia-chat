---
name: price-quote
description: Membuat estimasi/penawaran harga berdasarkan paket, jumlah lisensi, dan durasi kontrak — termasuk diskon term dan volume. Gunakan saat pengguna meminta penawaran, estimasi biaya, atau total harga berlangganan.
license: Proprietary
compatibility: Membaca assets/price-list.json; tool auto-diregistrasi dari scripts/.
tool:
  entrypoint: scripts/quote.py:price_quote
metadata:
  version: "1.0"
---
# Skill: Price Quote

Membuat penawaran harga yang akurat beserta rincian diskon.

## Langkah
1. Tanyakan/identifikasi tiga hal: **paket** (basic/pro/enterprise),
   **jumlah** lisensi, dan **durasi** kontrak (bulan).
2. Panggil tool `price_quote(package, quantity, term_months)`.
3. Jika `ok` = true, format hasilnya memakai template di
   [assets/quote-template.md](assets/quote-template.md).
4. Jika `ok` = false, sampaikan error dan tampilkan `available_packages`.

## Aturan harga & diskon
Lihat [references/pricing-rules.md](references/pricing-rules.md) untuk rincian
tingkat diskon term & volume. Data harga dasar ada di
[assets/price-list.json](assets/price-list.json).

## Menjalankan script langsung (opsional)
Logika perhitungan ada di [scripts/quote.py](scripts/quote.py) dan dapat diuji
mandiri:
```bash
python scripts/quote.py --package pro --qty 5 --term 12
```

## Contoh
- "Pro untuk 5 user setahun berapa?" → `price_quote("pro", 5, 12)` → format dengan template.
