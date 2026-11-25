"""Normalize indexed KB chunk documents for retrieval responses and LLM prompts.

Indexed shape (from chunk_and_embed) uses: chunk, chunk_semantic, title, tags, …
Legacy / prompt aliases: body, summary, content.
"""

from __future__ import annotations

from typing import Any, Mapping, MutableMapping, Optional


# Fields used by multi_match lexical search — must match indexed document keys.
LEXICAL_SEARCH_FIELDS = (
    "chunk^2",
    "chunk_semantic^2",
    "title^3",
    "tags",
)

ELSER_INFERENCE_ID = "elser-model-2-endpoint"


def chunk_body(doc: Mapping[str, Any]) -> str:
    """Best available text body from an indexed or legacy KB document."""
    for key in ("chunk", "chunk_semantic", "body", "summary", "content"):
        value = doc.get(key)
        if value:
            return str(value)
    return ""


def chunk_title(doc: Mapping[str, Any]) -> str:
    value = doc.get("title")
    if not value and isinstance(doc.get("meta_data"), dict):
        value = doc["meta_data"].get("title")
    return str(value) if value else ""


def normalize_kb_document(doc: Mapping[str, Any]) -> dict[str, Any]:
    """Return a stable view used by API responses and the LLM prompt builder."""
    body = chunk_body(doc)
    title = chunk_title(doc)
    tags = doc.get("tags") or []
    if not isinstance(tags, list):
        tags = list(tags) if tags else []
    return {
        "title": title,
        "chunk": body,
        "summary": body,  # alias for older callers
        "body": body,  # alias for LLM prompt
        "tags": tags,
        "chunk_no": doc.get("chunk_no", ""),
        "article_number": doc.get("article_number", ""),
        "sys_id": doc.get("sys_id", ""),
        "type": doc.get("type", ""),
    }


def to_llm_hit(doc: Mapping[str, Any]) -> dict[str, Any]:
    norm = normalize_kb_document(doc)
    return {
        "title": norm["title"],
        "summary": norm["summary"],
        "body": norm["body"],
        "chunk": norm["chunk"],
        "tags": norm["tags"],
    }


def to_related_article(doc: Mapping[str, Any]) -> dict[str, Any]:
    norm = normalize_kb_document(doc)
    return {
        "title": norm["title"],
        "summary": norm["summary"],
        "tags": norm["tags"],
        "chunk_no": norm["chunk_no"],
        "article_number": norm["article_number"],
    }


def make_document_id(sys_id: str, chunk_no: str) -> str:
    """Stable unique ES _id: avoids collisions across articles sharing titles/filenames."""
    sys_part = (sys_id or "unknown").strip() or "unknown"
    chunk_part = (chunk_no or "chunk").strip() or "chunk"
    return f"{sys_part}__{chunk_part}"


def safe_chunk_step(chunk_size: int, chunk_overlap: int) -> int:
    """Step size for sliding window; never 0 / negative (avoids infinite loop)."""
    size = int(chunk_size) if chunk_size else 512
    overlap = int(chunk_overlap) if chunk_overlap else 0
    if size < 1:
        size = 1
    if overlap < 0:
        overlap = 0
    if overlap >= size:
        overlap = size - 1
    return max(1, size - overlap)
