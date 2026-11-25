# Gemini Code Companion: RAG ServiceNow App

Agent-oriented overview. Prefer this file + `SECURITY.md` over outdated assumptions. If this conflicts with code, **code wins** — update this file.

## What it is

Python FastAPI backend: ServiceNow KB ingestion → Elasticsearch (ELSER sparse vectors) → ticket RAG with a **configurable** LLM provider.

## Stack (actual)

| Piece | Reality |
|-------|---------|
| API | FastAPI — `POST /retrieve`, `POST /rag`, `GET /healthz`, `GET /readyz`; `X-API-Key` when `API_KEY` set |
| Search | Elasticsearch 8.x + ELSER inference id `elser-model-2-endpoint` |
| LLM | `LLM_PROVIDER=huggingface` (default, lazy HF pipeline) or `azure_openai` (chat completions) |
| Config | `src/config.py`: process env > `.env` > `config.yaml` |
| Logging | stdlib `logging` via `src/utils/observability.py` (stdout). **Not** loguru file rotation |

## Key files

| File | Role |
|------|------|
| `README.md` | Human setup + runbook |
| `SECURITY.md` | Secrets rules |
| `requirements.txt` / `requirements-dev.txt` | Runtime / test deps |
| `.env.example` / `config.example.yaml` | Placeholder templates only |
| `src/api/main.py` | FastAPI entry |
| `src/config.py` | Config loader |
| `src/run_pipeline.py` | One-shot ingest (`limit=20`) |
| `src/run_scheduler.py` | Weekly scheduler |
| `src/run_schedular.py` | Deprecated alias |
| `src/rag/pipeline.py` | RAG orchestration |
| `src/rag/ticket_retrieval.py` | Ticket → ES query |
| `src/generation/llm.py` | Prompt + provider dispatch |
| `src/storage/elasticsearch.py` | ES client helpers |
| `src/servicenow/fetch_kb.py` | KB fetch |
| `src/servicenow/fetch_attachments.py` | Attachment fetch/extract |

## LLM config

```bash
LLM_PROVIDER=huggingface   # or azure_openai
LLM_MODEL=google/flan-t5-base
# azure_openai also needs:
# AZURE_OPENAI_API_KEY / AZURE_OPENAI_ENDPOINT / AZURE_OPENAI_DEPLOYMENT
```

## Setup (short)

```bash
pip install -r requirements.txt
cp .env.example .env
cp config.example.yaml config.yaml
# fill local files; never commit secrets
```

## Run

From repo root with `PYTHONPATH=.`:

```bash
PYTHONPATH=. python src/run_pipeline.py
PYTHONPATH=. python src/run_scheduler.py
PYTHONPATH=. uvicorn src.api.main:app --host 127.0.0.1 --port 8000
```

Swagger: `http://127.0.0.1:8000/docs`

## Tests / CI / Docker

```bash
pip install -r requirements-dev.txt
pytest tests -q
```

Use **dummy** keys only in tests and CI (see `.github/workflows/ci.yml`).
Runtime pins: `requirements.txt`. Container: `Dockerfile` + `docker-compose.yml` (no baked secrets).

## Conventions for agents

- Do not invent endpoints. Live routes: `POST /retrieve`, `POST /rag`, `GET /healthz`, `GET /readyz`.
- Protected routes need header `X-API-Key` when `API_KEY` is configured. Never log raw tickets or secrets.
- Prefer `src/run_scheduler.py` (not the deprecated `run_schedular.py` name).
- Select LLM via `LLM_PROVIDER`; do not hardcode provider or secrets in code.
