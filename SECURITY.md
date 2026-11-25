# Security and secrets

## Rules

- Never commit `.env` or `config.yaml`. Both are gitignored.
- Commit only `.env.example` and `config.example.yaml` with placeholders (`your-*`).
- Never paste real API keys, passwords, or tokens into chat, tickets, docs, or tests.
- Tests must use dummy values only (see `tests/phase_a/`).
- Rotate any credential that was shared, logged, or stored outside a secret manager.

## Config precedence

1. Process environment variables (highest)
2. Optional `.env` (loaded without overriding existing process env)
3. Optional `config.yaml`

Override paths for tests or containers:

- `RAG_CONFIG_PATH` — YAML file path
- `RAG_ENV_FILE` — dotenv file path (set empty via loader API to skip)

## Local setup

```sh
cp .env.example .env
cp config.example.yaml config.yaml
# edit local files only; keep them off git
```

## If secrets leaked

1. Rotate ServiceNow, Azure OpenAI, Elasticsearch, and app API keys at the provider.
2. Replace local `.env` / `config.yaml` with new values.
3. Confirm examples still contain placeholders only.
4. If a git history ever held secrets, purge history or abandon the repo and start clean.

## API authentication

- Set `API_KEY` in `.env` / `config.yaml` (placeholder in examples only).
- Clients must send `X-API-Key: <value>` on `POST /retrieve` and `POST /rag`.
- `/healthz` and `/readyz` stay open for probes.
- In production set `ENVIRONMENT=production` (disables `/docs`) or `DISABLE_API_DOCS=true`.

## Logging

Use `src.config.redacted(config)` before logging config. Never log raw secret values or full ticket payloads with credentials.
