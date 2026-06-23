---
name: faq-lookup
description: Mencari jawaban FAQ resmi tentang layanan, harga, jam operasional, kontak, dan kebijakan refund. Gunakan saat pengguna menanyakan informasi yang mungkin ada di basis FAQ.
metadata:
  tool: lookup_faq
---
# Skill: FAQ Lookup

Skill untuk menjawab pertanyaan umum dengan jawaban resmi dari basis FAQ.

## Langkah
1. Identifikasi topik pertanyaan (mis. "harga", "refund", "jam operasional", "kontak").
2. Panggil tool `lookup_faq` dengan kata kunci topik tersebut.
3. Jika `found` = true, sampaikan `answer` apa adanya (jangan diubah artinya).
4. Jika `found` = false, jangan mengarang — sampaikan bahwa info belum tersedia
   dan arahkan ke support (lihat MEMORY.md / hasil tool).

## Contoh
- Input: "paket bulanannya berapa ya?" → `lookup_faq("harga")` → sampaikan harga.
- Input: "bisa refund nggak?" → `lookup_faq("refund")` → sampaikan kebijakan refund.
