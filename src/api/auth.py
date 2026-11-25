"""API key authentication for protected routes."""

from __future__ import annotations

import hmac
import logging
from typing import Optional

from fastapi import Header, HTTPException, status

from src.config import config, get_secret

logger = logging.getLogger("api_auth")


def configured_api_key() -> Optional[str]:
    return get_secret(config, "API_KEY")


def api_key_required() -> bool:
    """Enforce auth when an API key is configured."""
    return bool(configured_api_key())


async def require_api_key(x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    expected = configured_api_key()
    if not expected:
        # Dev mode: no key configured. Callers should set API_KEY before production.
        return None
    if not x_api_key or not hmac.compare_digest(x_api_key, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return True
