# RAG ServiceNow App

Backend RAG service for ServiceNow IT tickets: retrieve KB chunks from Elasticsearch (ELSER), then generate a solution with a local Hugging Face LLM.

---

## Current features (as implemented)

- Semantic retrieval via Elasticsearch ELSER inference id `elser-model-2-endpoint`
- RAG path: ticket JSON → related KB chunks → LLM text
- ServiceNow KB + attachment ingestion (chunk + ELSER sparse vectors → Elasticsearch)
- FastAPI endpoints: `POST /retrieve`, `POST /rag` (API key via `X-API-Key` when `API_KEY` set)
- Health: `GET /healthz`, `GET /readyz`
- Config via process env > `.env` > `config.yaml` (see [SECURITY.md](SECURITY.md))

**Not implemented yet:** rotating file logs under `logs/`, ES/LLM `--test` CLIs, index mapping helpers in code. Mistral is not a built-in provider — use `LLM_PROVIDER=huggingface` with a Mistral HF model id if needed.

---

## Directory structure

```
src/
  api/main.py                 # FastAPI app: /retrieve, /rag
  config.py                   # Config loader (env > .env > yaml)
  run_pipeline.py             # One-shot ingestion
  run_scheduler.py            # Weekly APScheduler wrapper
  run_schedular.py            # Deprecated alias → run_scheduler
  rag/
    pipeline.py               # RAG orchestration
    retrieval.py              # /retrieve helper
    ticket_retrieval.py       # Ticket → ES query
  generation/llm.py           # Configurable LLM (HF / Azure OpenAI)
  embeddings/
    chunk_and_embed.py        # Chunking + ELSER infer + index
    azure_openai.py           # Azure helper (also used by LLM_PROVIDER=azure_openai)
  servicenow/
    fetch_kb.py
    fetch_attachments.py
  storage/elasticsearch.py    # ES client helpers
  utils/observability.py      # stdlib logging helpers (stdout)
  types/article.py
SECURITY.md
.env.example
config.example.yaml
tests/phase_a/                # Secret/config tests (dummy keys)
tests/phase_b/                # Doc accuracy tests
tests/phase_c/                # RAG contract tests (mocked ES/LLM)
tests/phase_d/                # API hardening tests (dummy API_KEY)
tests/phase_e/                # Ops artifact tests (Docker/CI/pins)
Dockerfile / docker-compose.yml
.github/workflows/ci.yml
```

---

## Prerequisites

- Python 3.12+ recommended (project historically mixed 3.8+/3.12 notes; run on 3.12)
- Elasticsearch 8.10+ with ML enabled and an ELSER inference endpoint named `elser-model-2-endpoint`
- ServiceNow credentials for ingestion
- Optional: Azure OpenAI credentials only if you later wire that path (not active today)

---

## Setup

```sh
cd rag-servicenow-app
python -m venv .venv
# Windows: .venv\Scripts\activate
# Unix: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
cp config.example.yaml config.yaml
# Edit local .env / config.yaml only. Never commit real secrets.
```

Secret rules and rotation: [SECURITY.md](SECURITY.md).

Dependency extras for attachment parsing are already listed in `requirements.txt` (`pandas`, `openpyxl`, `python-pptx`, `beautifulsoup4`, `pdfplumber`, `python-docx`, `pytesseract`; `pywin32` on Windows only).

---

## Elasticsearch / ELSER

1. Install and start Elasticsearch 8.10+.
2. Enable ML (`xpack.ml.enabled: true`).
3. Deploy ELSER and create an **inference endpoint** whose id matches the code: `elser-model-2-endpoint` (see Elastic docs for your version; do not assume `.elser_model_1` deploy alone is enough).
4. Create the articles index/mapping to match fields produced by `src/embeddings/chunk_and_embed.py` (`chunk`, `chunk_semantic`, `title`, `tags`, `elser_*`, etc.). Mapping is **not** auto-created by `src/storage/elasticsearch.py` today.

---

## Run ingestion

From **repo root** so `src.*` imports resolve:

```sh
# Windows PowerShell
$env:PYTHONPATH = "."
python src/run_pipeline.py

# bash
PYTHONPATH=. python src/run_pipeline.py
```

Notes:

- Pipeline currently fetches `limit=20` articles per run.
- Scheduler: `PYTHONPATH=. python src/run_scheduler.py` (Sunday 02:00). Deprecated alias: `src/run_schedular.py`.
- Logging goes to **stdout** via stdlib `logging` (`src/utils/observability.py`). There is no rotating `logs/` file handler today.

---

## Run API

From repo root:

```sh
$env:PYTHONPATH = "."   # bash: export PYTHONPATH=.
uvicorn src.api.main:app --host 127.0.0.1 --port 8000
```

- Swagger: http://127.0.0.1:8000/docs (disabled when `ENVIRONMENT=production` or `DISABLE_API_DOCS=true`)
- Prefer `127.0.0.1`. Set `API_KEY` and send header `X-API-Key: <value>` on `/retrieve` and `/rag`.

### Endpoints

| Method | Path | Auth | Body / notes | Result |
|--------|------|------|--------------|--------|
| GET | `/healthz` | no | liveness | `{ status: ok }` |
| GET | `/readyz` | no | basic config check | `{ status: ready, ... }` |
| POST | `/retrieve` | `X-API-Key` if configured | requires `short_description` | Related articles |
| POST | `/rag` | `X-API-Key` if configured | requires `short_description` or `description` | `{ recommended_solution, related_articles }` |

Example ticket shape (dummy values):

```json
{
  "number": "INC001",
  "short_description": "VPN disconnects on Wi-Fi",
  "description": "User loses VPN when switching networks",
  "category": "Network",
  "subcategory": "VPN",
  "cmdb_ci": "vpn-gateway"
}
```

### LLM / AI provider (config or `.env`)

| Variable | Purpose | Example |
|----------|---------|---------|
| `LLM_PROVIDER` | Backend | `huggingface` (default) or `azure_openai` |
| `LLM_MODEL` / `HF_MODEL_NAME` | Hugging Face model id | `google/flan-t5-base` |
| `LLM_MAX_NEW_TOKENS` | Max generation tokens | `512` |
| `AZURE_OPENAI_API_KEY` | Azure key (when provider=azure) | placeholder only in examples |
| `AZURE_OPENAI_ENDPOINT` | Azure resource URL | `https://your-resource.openai.azure.com` |
| `AZURE_OPENAI_DEPLOYMENT` / `AZURE_OPENAI_MODEL` | Deployment name | `your-deployment-name` |
| `AZURE_OPENAI_API_VERSION` | API version | `2024-02-15-preview` |

HF models load lazily on first generate. Azure uses chat completions + `api-key` header (no live keys in repo).

---

## Tests

Dummy credentials only. Never point tests at real API keys.

```sh
pip install -r requirements-dev.txt
pytest tests/phase_a tests/phase_b tests/phase_c tests/phase_d tests/phase_e -q
```

CI runs the same suites on push/PR via [`.github/workflows/ci.yml`](.github/workflows/ci.yml) using dummy env vars only.

---

## Docker

No secrets in the image. Pass config at runtime (compose env / orchestrator secrets).

```sh
# API only (uses dummy default API_KEY unless you export a real local one — never commit it)
docker compose up --build api

# API + Elasticsearch 8.15 (profile)
docker compose --profile full up --build
```

- Image: `Dockerfile` (`python:3.12-slim`, `uvicorn src.api.main:app`)
- Compose defaults use placeholders / `dummy-*` values only
- Prefer mounting or injecting `.env` locally; `.env` and `config.yaml` are dockerignored

---

## Known limitations

- First HF generate downloads/loads the configured model (large image / memory)
- Compose Elasticsearch profile disables security for local convenience — enable TLS/auth for real deployments
- Ingestion still needs `TESSERACT_CMD` for OCR; Word COM is Windows-oriented

---

## Troubleshooting

- **ELSER / inference errors:** Confirm endpoint id `elser-model-2-endpoint` and ML is enabled.
- **Import errors (`src.*`):** Set `PYTHONPATH` to repo root.
- **Empty / wrong retrieval:** Index field names must match `chunk_and_embed` output; Phase C fixes query/prompt contract.
- **Secrets:** Do not paste keys into issues or chat. Rotate if exposed. See SECURITY.md.

---

## License

MIT License
