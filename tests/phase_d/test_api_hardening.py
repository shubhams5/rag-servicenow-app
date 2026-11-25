"""Phase D: auth, validation, health, safe errors (dummy API key only)."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from src.api.errors import raise_http_or_internal
from src.config import reload_config
from src.rag.exceptions import RetrievalError
from src.rag.ticket_retrieval import get_related_kbs


def test_healthz_open(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_readyz_ok(client):
    resp = client.get("/readyz")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ready"
    assert body["api_auth"] is True


def test_retrieve_requires_api_key(client):
    resp = client.post(
        "/retrieve",
        json={"short_description": "dummy vpn issue"},
    )
    assert resp.status_code == 401


def test_retrieve_rejects_wrong_api_key(client):
    resp = client.post(
        "/retrieve",
        json={"short_description": "dummy vpn issue"},
        headers={"X-API-Key": "wrong-dummy-key"},
    )
    assert resp.status_code == 401


def test_retrieve_validation_requires_short_description(client, dummy_api_key):
    resp = client.post(
        "/retrieve",
        json={"number": "INC1"},
        headers={"X-API-Key": dummy_api_key},
    )
    assert resp.status_code == 400
    assert "short_description" in resp.json()["detail"]


def test_retrieve_success_with_dummy_key(client, dummy_api_key, monkeypatch):
    monkeypatch.setattr(
        "src.api.main.retrieve_articles",
        AsyncMock(return_value=[{"title": "Dummy KB", "chunk": "dummy text"}]),
    )
    resp = client.post(
        "/retrieve",
        json={"short_description": "dummy vpn issue"},
        headers={"X-API-Key": dummy_api_key},
    )
    assert resp.status_code == 200
    assert resp.json()[0]["title"] == "Dummy KB"


def test_rag_preserves_404(client, dummy_api_key, monkeypatch):
    async def boom(ticket, generate_fn=None):
        raise HTTPException(status_code=404, detail="No related KBs found")

    monkeypatch.setattr("src.api.main.rag_ticket_pipeline", boom)
    resp = client.post(
        "/rag",
        json={"short_description": "dummy nothing"},
        headers={"X-API-Key": dummy_api_key},
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "No related KBs found"


def test_rag_hides_internal_exception_text(client, dummy_api_key, monkeypatch):
    async def boom(ticket, generate_fn=None):
        raise RuntimeError("secret-internal-host-should-not-leak")

    monkeypatch.setattr("src.api.main.rag_ticket_pipeline", boom)
    resp = client.post(
        "/rag",
        json={"short_description": "dummy nothing"},
        headers={"X-API-Key": dummy_api_key},
    )
    assert resp.status_code == 500
    assert resp.json()["detail"] == "Internal server error"
    assert "secret-internal-host" not in resp.text


def test_raise_http_or_internal_preserves_http():
    with pytest.raises(HTTPException) as exc:
        raise_http_or_internal(HTTPException(status_code=404, detail="missing"))
    assert exc.value.status_code == 404


def test_get_related_kbs_maps_backend_failure():
    class Boom:
        def custom_query_articles(self, *_a, **_k):
            raise ConnectionError("dummy es down")

    with pytest.raises(RetrievalError):
        get_related_kbs(
            {"short_description": "dummy"},
            es_client=Boom(),
        )


def test_ticket_field_max_length(client, dummy_api_key):
    resp = client.post(
        "/retrieve",
        json={"short_description": "x" * 2000},
        headers={"X-API-Key": dummy_api_key},
    )
    assert resp.status_code == 422


def test_servicenow_timeout_constant_present():
    from src.servicenow import fetch_kb, fetch_attachments

    assert fetch_kb.HTTP_TIMEOUT > 0
    assert fetch_attachments.HTTP_TIMEOUT > 0


def test_no_hardcoded_user_tesseract_path():
    text = open("src/servicenow/fetch_attachments.py", encoding="utf-8").read()
    assert "AppData\\Local\\Programs\\Tesseract-OCR" not in text
    assert "2000110149" not in text
