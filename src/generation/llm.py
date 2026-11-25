"""Configurable LLM providers for RAG solution generation.

Select via config / env:
  LLM_PROVIDER=huggingface|azure_openai   (default: huggingface)
  LLM_MODEL / HF_MODEL_NAME               HF model id (default: google/flan-t5-base)
  AZURE_OPENAI_API_KEY / AZURE_OPENAI_KEY
  AZURE_OPENAI_ENDPOINT
  AZURE_OPENAI_DEPLOYMENT / AZURE_OPENAI_MODEL
  AZURE_OPENAI_API_VERSION
  LLM_MAX_NEW_TOKENS
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional

import requests

from src.config import config, get_secret

logger = logging.getLogger("llm_generation")

# Lazy HF pipeline — avoid loading transformers unless provider needs it.
_hf_pipeline = None
_hf_model_name: Optional[str] = None


def get_provider_name(cfg: Optional[dict] = None) -> str:
    raw = str((cfg or config).get("LLM_PROVIDER", "huggingface")).strip().lower()
    aliases = {
        "hf": "huggingface",
        "hugging_face": "huggingface",
        "huggingface": "huggingface",
        "azure": "azure_openai",
        "azure_openai": "azure_openai",
        "azure-openai": "azure_openai",
    }
    return aliases.get(raw, raw)


def get_hf_model_name(cfg: Optional[dict] = None) -> str:
    c = cfg or config
    return str(c.get("LLM_MODEL") or c.get("HF_MODEL_NAME") or "google/flan-t5-base")


def get_max_new_tokens(cfg: Optional[dict] = None, default: int = 512) -> int:
    c = cfg or config
    try:
        return int(c.get("LLM_MAX_NEW_TOKENS", default) or default)
    except (TypeError, ValueError):
        return default


def build_rag_prompt(ticket: dict, kb_hits: list, max_kb_chars: int = 1500) -> str:
    from src.rag.ticket_retrieval import build_ticket_query_text

    logger.info("Building RAG prompt for ticket: %s", ticket.get("number", ""))
    ticket_text = build_ticket_query_text(ticket)
    kb_chunks = []
    for i, kb in enumerate(kb_hits, start=1):
        body = (
            kb.get("chunk")
            or kb.get("chunk_semantic")
            or kb.get("body")
            or kb.get("summary")
            or ""
        )
        if len(body) > max_kb_chars:
            body = body[:max_kb_chars] + "...(truncated)"
        kb_chunks.append(
            f"KB{i} Title: {kb.get('title', '')}\nKB{i} Content:\n{body}\n"
        )
    logger.info("Prepared %s KB chunks for prompt", len(kb_chunks))
    kb_context = "\n\n---\n\n".join(kb_chunks)
    prompt = (
        "You are an IT support expert working with ServiceNow incidents. You receive:\n"
        "1. An incident ticket with full context.\n"
        "2. A set of relevant knowledge base articles (KB1, KB2, ...).\n"
        "Your task:\n"
        "- Understand the incident.\n"
        "- Use ONLY the information in the KB articles to propose:\n"
        "  - Most likely root cause or diagnosis.\n"
        "  - A clear, ordered list of steps to resolve.\n"
        "  - Any important checks, cautions, or prerequisites.\n"
        "- If the KBs do not contain enough information, explicitly say that and suggest what info is missing.\n\n"
        "Format your answer as:\n"
        "Summary:\n- ...\n"
        "Probable Cause:\n- ...\n"
        "Resolution Steps:\n1. ...\n2. ...\n3. ...\n"
        "KB References:\n- KB1: <short note if used>\n- KB2: <short note if used>\n\n"
        f"Incident: {ticket_text}\n\nKnowledge Base Articles:\n{kb_context}"
    ).strip()
    logger.debug("Generated prompt for LLM: %s...", prompt[:500])
    return prompt


def _get_hf_pipeline(model_name: str):
    global _hf_pipeline, _hf_model_name
    if _hf_pipeline is None or _hf_model_name != model_name:
        from transformers import pipeline

        logger.info("Loading Hugging Face model: %s", model_name)
        _hf_pipeline = pipeline("text2text-generation", model=model_name)
        _hf_model_name = model_name
    return _hf_pipeline


def _generate_huggingface(prompt: str, max_new_tokens: int, cfg: dict) -> str:
    model_name = get_hf_model_name(cfg)
    llm = _get_hf_pipeline(model_name)
    result = llm(prompt, max_new_tokens=max_new_tokens)
    return result[0]["generated_text"].strip()


def _azure_chat_url(endpoint: str, deployment: str, api_version: str) -> str:
    base = endpoint.rstrip("/")
    return (
        f"{base}/openai/deployments/{deployment}/chat/completions"
        f"?api-version={api_version}"
    )


def _generate_azure_openai(prompt: str, max_new_tokens: int, cfg: dict) -> str:
    api_key = get_secret(cfg, "AZURE_OPENAI_API_KEY") or get_secret(cfg, "AZURE_OPENAI_KEY")
    endpoint = (cfg.get("AZURE_OPENAI_ENDPOINT") or "").strip()
    deployment = (
        cfg.get("AZURE_OPENAI_DEPLOYMENT")
        or cfg.get("AZURE_OPENAI_MODEL")
        or ""
    ).strip()
    api_version = str(cfg.get("AZURE_OPENAI_API_VERSION") or "2024-02-15-preview")
    timeout = float(cfg.get("HTTP_TIMEOUT_SECONDS", 30) or 30)

    if not api_key or not endpoint or not deployment:
        raise ValueError(
            "Azure OpenAI requires AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, "
            "and AZURE_OPENAI_DEPLOYMENT (or AZURE_OPENAI_MODEL)"
        )

    url = _azure_chat_url(endpoint, deployment, api_version)
    headers = {
        "Content-Type": "application/json",
        "api-key": api_key,
    }
    payload = {
        "messages": [
            {
                "role": "system",
                "content": "You are an IT support expert. Follow the user instructions exactly.",
            },
            {"role": "user", "content": prompt},
        ],
        "max_tokens": max_new_tokens,
        "temperature": 0.2,
    }
    response = requests.post(url, headers=headers, json=payload, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    choices = data.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    return str(message.get("content") or "").strip()


PROVIDERS: dict[str, Callable[[str, int, dict], str]] = {
    "huggingface": _generate_huggingface,
    "azure_openai": _generate_azure_openai,
}


def reset_llm_cache() -> None:
    """Clear cached HF pipeline (tests / provider switches)."""
    global _hf_pipeline, _hf_model_name
    _hf_pipeline = None
    _hf_model_name = None


def generate_solution(
    ticket: dict,
    kb_hits: list,
    max_new_tokens: Optional[int] = None,
    cfg: Optional[dict] = None,
    generate_fn: Optional[Callable[[str, int, dict], str]] = None,
) -> str:
    """Generate a solution using the configured LLM provider.

    generate_fn: optional injectable for tests (signature: prompt, max_tokens, cfg).
    """
    active_cfg: dict[str, Any] = dict(cfg) if cfg is not None else dict(config)
    tokens = (
        max_new_tokens
        if max_new_tokens is not None
        else get_max_new_tokens(active_cfg)
    )
    prompt = build_rag_prompt(ticket, kb_hits)
    provider = get_provider_name(active_cfg)
    logger.info("Generating solution with provider=%s", provider)

    if generate_fn is not None:
        text = generate_fn(prompt, tokens, active_cfg)
    else:
        handler = PROVIDERS.get(provider)
        if handler is None:
            supported = ", ".join(sorted(PROVIDERS))
            raise ValueError(
                f"Unsupported LLM_PROVIDER={provider!r}. Supported: {supported}"
            )
        text = handler(prompt, tokens, active_cfg)

    logger.info("LLM generation complete")
    return text
