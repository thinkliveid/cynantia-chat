# Cynantia Chat

Sistem **multi-agent** untuk **Google Chat**. Sebuah **orchestrator** menerima
mention/pesan dari space atau thread, lalu **mendelegasikan** ke **specialist**
yang sesuai untuk menjawab. Tiap specialist adalah **A2A server sendiri** dengan
**instruction, tools, dan memory sendiri**. Balasan dikirim **ke thread yang sama**
dan **context per-thread persisten** (Postgres). Model lewat **OpenAI**
(OpenAI-compatible). Deploy sebagai container di **VPS/server sendiri**.

## Arsitektur

```
User @mention di space/thread
        │
        ▼
Google Chat API ──event MESSAGE──► webhook (FastAPI, :8080)
        ▲                               │  ACK cepat, lalu (background):
        │                               ▼
        │                    ┌─ Orchestrator (LlmAgent) ──┐  Runner + DatabaseSessionService
        │                    │   delegasi via A2A          │  (Postgres: context per-thread)
        │                    ▼                             ▼
        │            RemoteA2aAgent                 RemoteA2aAgent
        │                    │                             │
        │           ┌────────┘                             └────────┐
        │           ▼  A2A                                   A2A     ▼
        │    faq_agent (:8002)                          math_agent (:8003)
        │    LlmAgent + tool lookup_faq                 LlmAgent + tool calculate
        │           │                                            │
        └───────────┴──── balas async ke thread ◄───────────────┘
              (Chat API: thread.name + REPLY_MESSAGE_FALLBACK_TO_NEW_THREAD)
```

### Service (docker-compose)
| Service | Isi | Port |
|---|---|---|
| `postgres` | Penyimpanan session/memory persisten | 5432 (internal) |
| `faq` | Specialist FAQ — A2A server (`lookup_faq`) | 8002 (internal) |
| `math` | Specialist Math — A2A server (`calculate`) | 8003 (internal) |
| `webhook`| Orchestrator + Runner persisten + balas ke thread | 8080 (publik) |

## Struktur

```
src/cynantia_chat/
├── config.py                      # konfigurasi + URL specialist
├── agents/
│   ├── model.py                   # helper model OpenAI (LiteLLM) bersama
│   ├── orchestrator.py            # agent utama: sub_agents = RemoteA2aAgent[...]
│   └── specialists/
│       ├── faq/   (agent.py + server.py)    # instruction & tool sendiri
│       └── math/  (agent.py + server.py)    # instruction & tool sendiri
└── chat/
    ├── app.py                     # webhook FastAPI (mention + thread + ACK)
    ├── agent_client.py            # Runner(orchestrator, DatabaseSessionService)
    └── chat_client.py             # Chat API -> balas async ke thread
```

## Menambah specialist baru

1. Buat `agents/specialists/<nama>/agent.py` → `root_agent = LlmAgent(..., tools=[...])`.
2. Buat `agents/specialists/<nama>/server.py` → `a2a_app = to_a2a(root_agent, port=...)`.
3. Tambah URL & port di [config.py](src/cynantia_chat/config.py).
4. Tambah satu `RemoteA2aAgent` ke `sub_agents` di [orchestrator.py](src/cynantia_chat/agents/orchestrator.py).
5. Tambah satu service di [docker-compose.yml](docker-compose.yml).

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
  - `@Cynantia berapa harga paketnya?` → diteruskan ke **faq_agent**.
  - `@Cynantia hitung 12*(3+4)` → diteruskan ke **math_agent**.
- Balas di thread yang sama → orchestrator mengingat context (persisten di Postgres).

## Pengembangan lokal (tanpa VPS)
```bash
pip install -e .

# Postgres lokal (atau pakai DATABASE_URL sqlite untuk coba cepat):
#   export DATABASE_URL="sqlite:///./cynantia.db"

# Terminal 1 — specialist FAQ:
uvicorn cynantia_chat.agents.specialists.faq.server:a2a_app --port 8002
# Terminal 2 — specialist Math:
uvicorn cynantia_chat.agents.specialists.math.server:a2a_app --port 8003
# Terminal 3 — webhook (orchestrator menunjuk ke localhost):
FAQ_AGENT_URL=http://localhost:8002 MATH_AGENT_URL=http://localhost:8003 \
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

- Streaming internal aktif lewat `RunConfig(streaming_mode=StreamingMode.SSE)`
  pada Runner orchestrator → `stream_agent()` meng-yield snapshot teks kumulatif.
- Patch di-*throttle* `_MIN_PATCH_INTERVAL` (default 1 detik) di
  [app.py](src/cynantia_chat/chat/app.py) agar aman dari rate limit Chat API.
- Lewat hop A2A ke specialist, granularitas bisa lebih kasar (per-event, tidak
  selalu per-token); efek tetap "tumbuh bertahap", hanya langkahnya lebih besar.
- Naikkan `_MIN_PATCH_INTERVAL` bila volume tinggi untuk mengurangi panggilan API.

## Catatan tentang persistensi & memory

- **Context per-thread** (riwayat percakapan yang dilihat pengguna) **persisten di
  Postgres** lewat `DatabaseSessionService` pada Runner orchestrator. `session_id` =
  nama thread Google Chat, jadi bertahan lintas restart.
- **Session per-specialist juga persisten**: tiap specialist di-host lewat
  `persistent_a2a_app()` ([agents/a2a.py](src/cynantia_chat/agents/a2a.py)) yang
  menyuntik Runner ber-`DatabaseSessionService` ke `to_a2a(..., runner=...)`. Data
  terisolasi per `app_name` (mis. `faq_agent`, `math_agent`) di Postgres yang sama.
- **Long-term memory lintas-sesi**: yang dipersisten di atas adalah *session state*.
  ADK belum punya long-term `memory_service` berbasis SQL bawaan (opsi persisten saat
  ini Vertex). `memory_service` specialist masih in-memory; cukup untuk sebagian besar
  kasus karena konteks per-thread sudah persisten.

## Catatan versi
`google-adk` / `a2a-sdk` cepat berubah. Project ini memakai abstraksi ADK
(`to_a2a`, `RemoteA2aAgent`, `DatabaseSessionService`) yang relatif stabil. Jika ada
perubahan API setelah upgrade, cek: `agents/specialists/*/server.py`,
`agents/orchestrator.py`, dan `chat/agent_client.py`.
