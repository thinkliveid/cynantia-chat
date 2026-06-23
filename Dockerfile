# Satu image dipakai semua service; command di-override per service di compose.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml ./
COPY src ./src
# Konfigurasi agent berbasis Markdown (AGENT.md / MEMORY.md / SKILLS.md).
COPY agents_config ./agents_config

RUN pip install --upgrade pip && pip install .

# Default: webhook. Service lain meng-override `command` di docker-compose.yml.
CMD ["uvicorn", "cynantia_chat.chat.app:app", "--host", "0.0.0.0", "--port", "8080"]
