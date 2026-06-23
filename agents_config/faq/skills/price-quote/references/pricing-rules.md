# Aturan Harga & Diskon

Harga dasar per paket (per lisensi per bulan) ada di `assets/price-list.json`.

## Diskon durasi (term)
| Durasi kontrak | Diskon |
|---|---|
| ≥ 12 bulan | 20% |
| ≥ 6 bulan | 10% |
| < 6 bulan | 0% |

## Diskon volume
| Jumlah lisensi | Diskon tambahan |
|---|---|
| ≥ 10 | 10% |
| ≥ 5 | 5% |
| < 5 | 0% |

## Rumus
```
biaya_bulanan_kotor = harga_satuan × jumlah
biaya_bulanan_bersih = biaya_bulanan_kotor × (1 − diskon_term) × (1 − diskon_volume)
total_kontrak        = biaya_bulanan_bersih × durasi_bulan
```

Diskon term dan volume bersifat **multiplikatif** (dikalikan bertingkat, bukan
dijumlahkan). Semua nilai akhir dibulatkan ke rupiah terdekat.
