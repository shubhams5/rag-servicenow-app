"""Safe HTTP error helpers — never leak internal exception strings to clients."""

from __future__ import annotations

import logging

from fastapi import HTTPException

logger = logging.getLogger("api_errors")


def raise_http_or_internal(exc: BaseException, *, public_500: str = "Internal server error") -> None:
    """Re-raise HTTPException; map everything else to a generic 500."""
    if isinstance(exc, HTTPException):
        raise exc
    logger.exception("Unhandled error: %s", type(exc).__name__)
    raise HTTPException(status_code=500, detail=public_500) from exc
