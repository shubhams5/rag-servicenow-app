"""FastAPI entrypoint — hardened request surface (Phase D)."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator

from src.api.auth import api_key_required, require_api_key
from src.api.errors import raise_http_or_internal
from src.config import config
from src.rag.pipeline import rag_ticket_pipeline
from src.rag.retrieval import retrieve_articles

logger = logging.getLogger("api")

_ENV = str(config.get("ENVIRONMENT", "development")).lower()
_DISABLE_DOCS = str(config.get("DISABLE_API_DOCS", "")).lower() in {
    "1",
    "true",
    "yes",
} or _ENV == "production"

app = FastAPI(
    title="RAG ServiceNow App",
    docs_url=None if _DISABLE_DOCS else "/docs",
    redoc_url=None if _DISABLE_DOCS else "/redoc",
    openapi_url=None if _DISABLE_DOCS else "/openapi.json",
)

MAX_TEXT = 4000
MAX_SHORT = 1024
MAX_ID = 128


class TicketRequest(BaseModel):
    number: Optional[str] = Field(default=None, max_length=MAX_ID)
    short_description: Optional[str] = Field(default=None, max_length=MAX_SHORT)
    description: Optional[str] = Field(default=None, max_length=MAX_TEXT)
    category: Optional[str] = Field(default=None, max_length=MAX_ID)
    subcategory: Optional[str] = Field(default=None, max_length=MAX_ID)
    cmdb_ci: Optional[str] = Field(default=None, max_length=MAX_ID)

    @field_validator(
        "number",
        "short_description",
        "description",
        "category",
        "subcategory",
        "cmdb_ci",
        mode="before",
    )
    @classmethod
    def empty_str_to_none(cls, value):
        if value is None:
            return None
        if isinstance(value, str) and not value.strip():
            return None
        return value


def _ticket_dict(ticket: TicketRequest) -> dict:
    # Pydantic v1/v2 compatibility
    if hasattr(ticket, "model_dump"):
        return ticket.model_dump()
    return ticket.dict()


@app.on_event("startup")
async def _startup_security_notice():
    if not api_key_required():
        logger.warning(
            "API_KEY is not set — /retrieve and /rag are open. "
            "Set API_KEY before exposing this service."
        )
    if _DISABLE_DOCS:
        logger.info("API docs disabled (production or DISABLE_API_DOCS)")


@app.get("/healthz")
async def healthz():
    """Liveness — no auth, no dependency checks."""
    return {"status": "ok"}


@app.get("/readyz")
async def readyz():
    """Readiness — basic config presence; does not call external APIs."""
    missing = []
    if not config.get("ELASTICSEARCH_HOST"):
        missing.append("ELASTICSEARCH_HOST")
    if not config.get("ELASTICSEARCH_INDEX_NAME"):
        missing.append("ELASTICSEARCH_INDEX_NAME")
    if missing:
        raise HTTPException(
            status_code=503,
            detail={"status": "not_ready", "missing": missing},
        )
    return {
        "status": "ready",
        "api_auth": api_key_required(),
        "docs_enabled": not _DISABLE_DOCS,
    }


@app.post("/retrieve")
async def retrieve(
    ticket_request: TicketRequest,
    _: None = Depends(require_api_key),
):
    if not ticket_request.short_description:
        raise HTTPException(
            status_code=400,
            detail="short_description is required",
        )
    try:
        return await retrieve_articles(ticket_request.short_description)
    except Exception as exc:
        raise_http_or_internal(exc)


@app.post("/rag")
async def rag(
    ticket_request: TicketRequest,
    _: None = Depends(require_api_key),
):
    if not ticket_request.short_description and not ticket_request.description:
        raise HTTPException(
            status_code=400,
            detail="short_description or description is required",
        )
    try:
        return await rag_ticket_pipeline(_ticket_dict(ticket_request))
    except Exception as exc:
        raise_http_or_internal(exc)


if __name__ == "__main__":
    import uvicorn

    # Local default: loopback. Use an explicit host env only when you intend to expose.
    host = config.get("API_HOST", "127.0.0.1")
    port = int(config.get("API_PORT", 8000) or 8000)
    uvicorn.run(app, host=host, port=port)
