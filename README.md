# Cynantia Chat

Sistem **multi-agent** untuk **Google Chat**. Sebuah **orchestrator** menerima
mention/pesan dari space atau thread, lalu **mendelegasikan** ke **specialist**
yang sesuai untuk menjawab. Specialist **ditemukan otomatis dari folder** —
tambah specialist cukup dengan membuat folder berisi Markdown, lalu restart.
Balasan dikirim **ke thread yang sama** (streaming bertahap) dan **context
per-thread persisten** (Postgres). Model lewat **OpenAI** (OpenAI-compatible).
Deploy sebagai container di **VPS/server sendiri**.

## Arsitektur

```
User @mention di space/thread
        │
        ▼
Google Chat API ──event MESSAGE──► webhook (FastAPI, :8080)
        ▲                               │  ACK cepat, lalu (background):
        │                               ▼
        │              Orchestrator (LlmAgent) + Runner + DatabaseSessionService
        │                     │   delegasi (ADK sub-agent transfer)   (Postgres)
        │              ┌──────┴───────────────┐
        │              ▼                       ▼
        │        faq (LlmAgent)          math (LlmAgent)      ← auto-discovered
        │        tool: lookup_faq        tool: calculate         dari agents_config/
        │              │                       │
        └──────────────┴── balas async ke thread (streaming) ──┘
              (Chat API: thread.name + REPLY_MESSAGE_FALLBACK_TO_NEW_THREAD)
```

Specialist berjalan **in-process** di dalam orchestrator (bukan container
terpisah). Delegasi memakai mekanisme sub-agent native ADK.

### Service (docker-compose)
| Service | Isi | Port |
|---|---|---|
| `postgres` | Penyimpanan session/context persisten | 5432 (internal) |
| `webhook` | Orchestrator + specialist (in-process) + balas ke thread | 8080 (publik) |

## Struktur

```
agents_config/                    # PERILAKU & DAFTAR agent diatur di sini (Markdown)
├── orchestrator/ (AGENT.md, MEMORY.md)              # agent utama (perute)
├── faq/                                             # specialist
│   ├── AGENT.md, MEMORY.md
│   └── skills/faq-lookup/SKILL.md                   # Agent Skills (agentskills.io)
└── math/                                            # specialist
    ├── AGENT.md, MEMORY.md
    └── skills/arithmetic-calculator/SKILL.md
    (buat folder baru di sini = specialist baru)

src/cynantia_chat/
├── config.py                      # konfigurasi (model, DB, dll.)
├── agents/
│   ├── model.py                   # helper model OpenAI (LiteLLM) bersama
│   ├── prompt_loader.py           # baca AGENT/MEMORY.md + skills/ (Agent Skills)
│   ├── tools.py                   # fungsi tool + registry TOOLS
│   ├── discovery.py               # pindai agents_config/ -> daftar specialist
│   └── orchestrator.py            # agent utama: sub_agents = hasil discovery
└── chat/
    ├── app.py                     # webhook FastAPI (mention + thread + streaming)
    ├── agent_client.py            # Runner(orchestrator, DatabaseSessionService)
    └── chat_client.py             # Chat API -> balas async ke thread
```

## Menambah specialist baru (cukup folder + restart)

1. Buat folder `agents_config/<nama>/`.
2. Isi `AGENT.md` (wajib). Boleh diawali frontmatter YAML:
   ```markdown
   ---
   description: Ringkasan singkat — dipakai orchestrator untuk memilih specialist ini.
   tools: [nama_tool]        # opsional; kosongkan untuk specialist tanpa tool
   ---
   # Peran: ...
   ```
3. (Opsional) `MEMORY.md` (fakta tetap) dan/atau folder `skills/` (lihat di bawah).
4. **Restart** service (`docker compose restart webhook` atau `systemctl restart cynantia-webhook`).

Orchestrator otomatis menemukan folder baru, menjadikannya specialist, dan
menambahkannya ke daftar delegasi — **tanpa mengubah kode atau compose**.

> **Tools** harus berupa fungsi Python (eksekutabel) — tidak bisa dari Markdown.
> Specialist "folder saja" = prompt-only (tanpa tool). Untuk memberi tool: pakai
> registry bersama di [tools.py](src/cynantia_chat/agents/tools.py) **atau**
> auto-registrasi dari skill via `tool.entrypoint` di SKILL.md (lihat
> [bagian Skills](#tool-dua-cara-mendaftarkan)) — yang kedua tanpa edit tools.py.

## Mengatur perilaku agent lewat Markdown

Tiap agent membaca konfigurasinya dari `agents_config/<nama>/`:

| File | Isi | Wajib? |
|---|---|---|
| `AGENT.md` | Peran & instruksi (+ frontmatter `description`/`tools`) | ✅ |
| `MEMORY.md` | Pengetahuan/fakta tetap yang selalu diingat | opsional |
| `skills/<nama>/SKILL.md` | Skill berformat **Agent Skills** (lihat di bawah) | opsional |

Digabung jadi satu instruction oleh
[prompt_loader.py](src/cynantia_chat/agents/prompt_loader.py). Folder di-mount
read-only di Docker, jadi edit Markdown lalu restart service (tanpa rebuild).
Lokasi folder bisa dipindah lewat env `AGENTS_CONFIG_DIR`.

### Skills (standar Agent Skills)

Skill mengikuti format terbuka [agentskills.io](https://agentskills.io): satu
folder per skill berisi `SKILL.md` dengan frontmatter `name` + `description`.

```
agents_config/faq/skills/faq-lookup/SKILL.md
```
```markdown
---
name: faq-lookup          # lowercase a-z 0-9 dan '-', sama dengan nama folder
description: Apa yang dilakukan skill + KAPAN dipakai (≤1024 char).
metadata:
  tool: lookup_faq        # opsional, penanda tool terkait
---
# Skill: ...
Instruksi langkah-demi-langkah, contoh, edge case.
```

- `name` & `description` **wajib**; opsional `license`, `compatibility`,
  `metadata`, `allowed-tools`, dan `tool.entrypoint` (lihat di bawah).
- Validasi dengan `skills-ref validate ./agents_config/faq/skills/faq-lookup`.
- Loader menyuntikkan ringkasan tiap skill ke instruksi agent (progressive
  disclosure disederhanakan: body skill ikut digabung).
- Skill boleh membawa `scripts/`, `references/`, `assets/` sesuai spec.

### Tool: dua cara mendaftarkan

Sebuah specialist memperoleh tool dari dua sumber (digabung otomatis):

1. **Registry bersama** — fungsi di [tools.py](src/cynantia_chat/agents/tools.py),
   dirujuk lewat `tools: [nama]` di frontmatter `AGENT.md`. Cocok untuk tool yang
   dipakai banyak agent.
2. **Auto-registrasi dari skill** — taruh fungsi tool *self-contained* di
   `scripts/` lalu deklarasikan di `SKILL.md`:
   ```yaml
   tool:
     entrypoint: scripts/quote.py:price_quote
   ```
   Fungsi itu di-import & didaftarkan otomatis **tanpa menyentuh tools.py**.
   Syarat: fungsi punya type hints + docstring dan memuat asset-nya sendiri.

> Auto-registrasi meng-*import* script dari `agents_config/` saat startup — aman
> selama folder config setara-tepercaya dengan kode (operator yang sama).

**Contoh skill lengkap** (ketiga folder opsional + auto-tool) di
`agents_config/faq/skills/price-quote/`:
```
price-quote/
├── SKILL.md                    # metadata + instruksi + tool.entrypoint
├── scripts/quote.py            # price_quote() self-contained (auto-jadi tool)
├── references/pricing-rules.md # dokumentasi aturan diskon
└── assets/
    ├── price-list.json         # data harga (dimuat sendiri oleh script)
    └── quote-template.md       # template balasan
```
Skill ini benar-benar fungsional: tool-nya datang langsung dari `scripts/quote.py`,
tanpa entri apa pun di `tools.py`.

> 📦 **Deploy ke VPS, pasang di Workspace, dan publikasi ke Marketplace:** lihat
> panduan lengkap di [DEPLOY.md](DEPLOY.md).

## Prasyarat

- **Google Workspace** (Business/Enterprise) untuk mendaftarkan Chat app.
- **GCP project** dengan **Google Chat API** di-enable (gratis; tanpa Vertex).
- **Service account** + JSON key (untuk kirim balasan async).
- **OPENAI_API_KEY**.
- VPS dengan **Docker** + **Docker Compose**.

## Setup

```bash
cp .env.example .env          # isi OPENAI_API_KEY dll.
mkdir -p secrets              # taruh service account JSON:
#   secrets/service-account.json
```

### Daftarkan Google Chat app
GCP Console → **Google Chat API → Configuration**:
- Functionality: aktifkan terima 1:1 & join spaces.
- Connection: **HTTP endpoint URL** = URL publik webhook (HTTPS), mis. `https://chat.domainmu.com/`.
- Catat **Project number** → isi `CHAT_AUDIENCE` di `.env`.

### Jalankan (VPS)
```bash
docker compose up -d --build
docker compose logs -f
```
Arahkan reverse proxy HTTPS publik → `localhost:8080`, pakai URL itu sebagai endpoint.

### Coba
- Tambahkan app ke space, lalu:
  - `@Cynantia berapa harga paketnya?` → didelegasikan ke specialist **faq**.
  - `@Cynantia hitung 12*(3+4)` → didelegasikan ke specialist **math**.
- Balas di thread yang sama → context diingat (persisten di Postgres).

## Pengembangan lokal (tanpa VPS)
```bash
pip install -e .

# Postgres lokal, atau untuk coba cepat pakai sqlite:
#   export DATABASE_URL="sqlite:///./cynantia.db"

uvicorn cynantia_chat.chat.app:app --port 8080
```
Ekspos `:8080` lewat tunnel (cloudflared/ngrok) agar Google Chat bisa menjangkau.

## Mengganti model / provider
Semua OpenAI-compatible — ubah `.env`:

| Provider | `OPENAI_BASE_URL` | `AGENT_MODEL` |
|---|---|---|
| OpenAI | `https://api.openai.com/v1` | `openai/gpt-4o-mini` |
| OpenRouter | `https://openrouter.ai/api/v1` | `openai/anthropic/claude-3.5-sonnet` |
| vLLM lokal | `http://host:8000/v1` | `openai/<nama-model>` |

## Streaming (efek "mengetik")

Google Chat tidak punya streaming token native, jadi disimulasikan: webhook
membuat pesan saat potongan pertama tiba (`messages.create`) lalu mem-*patch*
teksnya berkala (`messages.patch`) seiring jawaban mengalir.

- Streaming internal aktif lewat `RunConfig(streaming_mode=StreamingMode.SSE)` →
  `stream_agent()` meng-yield snapshot teks kumulatif.
- Patch di-*throttle* `_MIN_PATCH_INTERVAL` (default 1 detik) di
  [app.py](src/cynantia_chat/chat/app.py) agar aman dari rate limit Chat API.
- Saat delegasi ke specialist, granularitas bisa lebih kasar (per-event); efek
  tetap "tumbuh bertahap". Naikkan interval bila volume tinggi.

## Catatan persistensi & memory

- **Context per-thread** persisten di Postgres via `DatabaseSessionService`.
  `session_id` = nama thread Google Chat → bertahan lintas restart. Karena
  specialist berjalan in-process dalam Runner yang sama, state mereka ikut tersimpan.
- **Long-term memory lintas-sesi**: yang dipersisten adalah *session state*. ADK
  belum punya `memory_service` berbasis SQL bawaan (opsi persisten saat ini Vertex);
  `memory_service` masih in-memory — cukup karena context per-thread sudah persisten.

## Catatan topologi & versi

- **In-process**: orchestrator dan semua specialist jalan dalam satu pross; delegasi
  memakai sub-agent transfer ADK (bukan protokol A2A di kabel). Pilihan ini ditukar
  demi kemudahan "tambah folder + restart". Bila butuh tiap specialist sebagai server
  A2A terpisah, itu topologi distributed (di luar setup ini).
- `google-adk` cepat berubah. Titik yang perlu dicek bila ada perubahan API:
  `agents/discovery.py`, `agents/orchestrator.py`, dan `chat/agent_client.py`.
