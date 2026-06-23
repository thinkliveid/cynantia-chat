# Panduan Deploy & Publikasi — Cynantia Chat

Panduan lengkap: deploy backend ke VPS → daftarkan di Google Chat → pasang di
Google Workspace milikmu → publikasikan ke **Google Workspace Marketplace** agar
workspace lain bisa memasang.

Daftar isi:
- [A. Deploy backend ke VPS (Docker)](#a-deploy-backend-ke-vps-docker)
- [B. Siapkan GCP project & service account](#b-siapkan-gcp-project--service-account)
- [C. Reverse proxy HTTPS](#c-reverse-proxy-https-wajib)
- [D. Konfigurasi Google Chat API](#d-konfigurasi-google-chat-api)
- [E. Pasang di Google Workspace-mu](#e-pasang-di-google-workspace-mu)
- [F. Publikasi ke Google Workspace Marketplace](#f-publikasi-ke-google-workspace-marketplace)
- [G. Checklist & masalah umum](#g-checklist--masalah-umum)

---

## A. Deploy backend ke VPS (Docker)

Prasyarat di VPS: Docker + Docker Compose, domain yang mengarah ke IP VPS.

```bash
git clone <repo-mu> cynantia-chat && cd cynantia-chat
cp .env.example .env          # isi OPENAI_API_KEY, dll.
mkdir -p secrets              # service account JSON ditaruh di sini (langkah B)
```

Edit `.env` minimal:
```ini
OPENAI_API_KEY=sk-...
AGENT_MODEL=openai/gpt-4o-mini
DATABASE_URL=postgresql+psycopg://cynantia:cynantia@postgres:5432/cynantia
CHAT_AUDIENCE=          # diisi project NUMBER setelah langkah B
```

Jalankan:
```bash
docker compose up -d --build
docker compose ps
docker compose logs -f webhook
```

Service `webhook` listen di `:8080` (lokal). Akses publik diberikan reverse proxy
(langkah C). Cek sehat: `curl localhost:8080/healthz` → `{"status":"ok"}`.

---

## B. Siapkan GCP project & service account

1. Buat/pilih project di [Google Cloud Console](https://console.cloud.google.com).
   Catat **Project number** (Dashboard) → masukkan ke `CHAT_AUDIENCE` di `.env`,
   lalu `docker compose up -d` ulang.
2. **Enable API**: APIs & Services → Enable APIs → aktifkan **Google Chat API**.
3. **Service account** (agar app bisa mengirim/patch pesan secara async):
   - IAM & Admin → Service Accounts → Create.
   - Tidak perlu role IAM khusus untuk Chat app auth dasar.
   - Buka service account → Keys → Add key → JSON → unduh.
   - Simpan sebagai `secrets/service-account.json` di VPS (path ini sudah
     di-mount read-only oleh `webhook` di docker-compose).

> Chat app memakai **app authentication** (kredensial service account, scope
> `chat.bot`) untuk memposting balasan — itulah yang dipakai `chat_client.py`.

---

## C. Reverse proxy HTTPS (wajib)

Google Chat hanya memanggil **HTTPS** endpoint publik. Contoh dengan **Caddy**
(TLS otomatis via Let's Encrypt). Buat `Caddyfile`:

```caddy
chat.domainmu.com {
    reverse_proxy localhost:8080
}
```

Jalankan Caddy (mis. service systemd atau container). Setelah aktif, endpoint
publikmu: `https://chat.domainmu.com/`. Uji: `curl https://chat.domainmu.com/healthz`.

> Alternatif: Nginx + certbot, atau Cloudflare Tunnel. Yang penting endpoint akhir
> HTTPS dan meneruskan ke `webhook:8080`.

---

## D. Konfigurasi Google Chat API

Console → **Google Chat API → Configuration**:

| Kolom | Isi |
|---|---|
| **App name** | mis. `Cynantia` (maks 25 karakter) |
| **Avatar URL** | URL HTTPS gambar 256×256 (PNG/JPEG) |
| **Description** | deskripsi singkat (maks 40 karakter) |
| **Functionality** | centang *Receive 1:1 messages* dan *Join spaces and group conversations* |
| **Connection settings** | pilih **HTTP endpoint URL** → `https://chat.domainmu.com/` |
| **Visibility** | tentukan siapa yang bisa memakai (lihat langkah E) |
| **Logs** | (opsional) centang *Log errors to Logging* |

Simpan. Verifikasi token: pastikan `CHAT_AUDIENCE` = Project number agar webhook
menerima request dari Google Chat ([app.py](src/cynantia_chat/chat/app.py)).

> **HTTP endpoint** vs **Cloud Pub/Sub**: panduan ini memakai HTTP endpoint
> (paling sederhana untuk VPS). Pub/Sub berguna bila webhook tak bisa diekspos publik.

---

## E. Pasang di Google Workspace-mu

Masih di halaman **Configuration**, atur **Visibility**:

- **Untuk diri/tim**: masukkan alamat email atau grup tertentu di domainmu.
- **Seluruh organisasi**: pilih agar tersedia bagi semua orang di domain
  (butuh hak admin / persetujuan admin Workspace).

Lalu di klien Google Chat:
1. Buka Chat → **New chat / Find apps** → cari nama app (`Cynantia`).
2. Tambahkan ke **space** atau mulai **DM**.
3. Di space, **mention** app: `@Cynantia ...`. Di DM, kirim pesan biasa.

App akan membalas di **thread yang sama** (streaming bertahap).

> Jika app tidak muncul: pastikan emailmu termasuk dalam Visibility, dan admin
> Workspace mengizinkan Chat apps internal (Admin console → Apps → Google
> Workspace → Google Chat → Chat apps settings).

---

## F. Publikasi ke Google Workspace Marketplace

Agar **workspace lain** bisa memasang, app harus dipublikasikan via **Google
Workspace Marketplace**. Garis besar (semua di Cloud Console, project yang sama):

### 1. OAuth consent screen
APIs & Services → **OAuth consent screen**:
- User type: **External** (untuk publik) atau **Internal** (hanya domainmu).
- Isi App name, support email, logo, domain, link Privacy Policy & Terms (wajib,
  harus URL publik yang valid).
- **Scopes**: tambahkan scope yang dipakai. Chat app berbasis app-auth memakai
  `https://www.googleapis.com/auth/chat.bot`. Jika menambah fitur yang mengakses
  data user, tambahkan scope terkait (bisa memicu verifikasi lebih ketat).

### 2. Enable Marketplace SDK
APIs & Services → Enable APIs → aktifkan **Google Workspace Marketplace SDK**.

### 3. App Configuration (Marketplace SDK)
Marketplace SDK → **App Configuration**:
- **Visibility/Availability**: Public (semua), Unlisted (lewat link), atau Private
  (domain tertentu).
- **Installation**: Admin-only install dan/atau individual install.
- **App integrations**: tambahkan **Google Chat app** (hubungkan ke konfigurasi
  Chat API di langkah D).
- **OAuth scopes**: daftar scope HARUS sama persis dengan OAuth consent screen.
- **Developer info & links**: terms, privacy, support.

### 4. Store listing
Marketplace SDK → **Store Listing**:
- Nama, deskripsi, kategori, bahasa.
- Aset grafis: ikon, screenshot, banner (sesuai ukuran yang diminta).
- Link dukungan & kebijakan.
- **Publish** untuk mengirim ke review.

### 5. Review & verifikasi OAuth
- App listing **tidak akan disetujui** sampai verifikasi OAuth (bila pakai
  sensitive/restricted scopes) selesai.
- Verifikasi OAuth umumnya minta **video demo** alur penggunaan scope + halaman
  privasi yang sah + verifikasi kepemilikan domain.
- Setelah disetujui, app muncul di Marketplace dan admin/end-user workspace lain
  bisa memasang sesuai setelan visibility.

> Estimasi: verifikasi OAuth + review listing bisa makan **beberapa hari s/d
> minggu**. Siapkan domain, privacy policy, terms, dan video demo lebih awal.

---

## G. Checklist & masalah umum

**Checklist sebelum publik**
- [ ] `docker compose ps` semua `healthy/up` (postgres, faq, math, webhook)
- [ ] `https://chat.domainmu.com/healthz` mengembalikan ok (TLS valid)
- [ ] `CHAT_AUDIENCE` = Project number; verifikasi token aktif
- [ ] `secrets/service-account.json` ada & benar
- [ ] Privacy Policy & Terms URL publik tersedia
- [ ] OAuth consent screen + scope konsisten dengan Marketplace SDK

**Masalah umum**
| Gejala | Kemungkinan sebab |
|---|---|
| App tak membalas | Endpoint bukan HTTPS / TLS invalid / `webhook` down / token ditolak (CHAT_AUDIENCE salah) |
| 401 di log webhook | `CHAT_AUDIENCE` tidak cocok dengan Project number |
| Balasan tak masuk thread | `service-account.json` salah / scope bukan `chat.bot` |
| Specialist error saat start | Postgres belum siap / `DATABASE_URL` salah |
| App tak muncul di Chat | Email tidak ada di Visibility / admin blokir Chat apps |

---

### Referensi
- Publish ke Marketplace: https://developers.google.com/workspace/marketplace/how-to-publish
- Konfigurasi Marketplace SDK: https://developers.google.com/workspace/marketplace/enable-configure-sdk
- OAuth consent (Marketplace): https://developers.google.com/workspace/marketplace/configure-oauth-consent-screen
- Auth Chat apps: https://developers.google.com/workspace/chat/authenticate-authorize
