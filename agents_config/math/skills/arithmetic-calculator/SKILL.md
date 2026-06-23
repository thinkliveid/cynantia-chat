---
name: arithmetic-calculator
description: Menghitung ekspresi aritmetika (tambah, kurang, kali, bagi, pangkat, modulo, kurung) secara akurat. Gunakan setiap kali pengguna meminta perhitungan numerik.
metadata:
  tool: calculate
---
# Skill: Arithmetic Calculator

Skill untuk menyelesaikan perhitungan numerik dengan tepat.

## Langkah
1. Susun ekspresi aritmetika dari pertanyaan pengguna (mis. "2*(3+4)/5").
2. Panggil tool `calculate` dengan ekspresi tersebut sebagai string.
3. Jika `ok` = true, sampaikan `result` dan, bila perlu, langkah singkatnya.
4. Jika `ok` = false, jelaskan errornya secara ramah dan minta klarifikasi.

## Catatan
- JANGAN menghitung di kepala — selalu pakai tool agar akurat.
- Operator didukung: `+ - * / // % **` dan kurung `( )`.
