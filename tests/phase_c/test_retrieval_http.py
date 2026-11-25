"""Phase C: retrieve helpers preserve HTTPException (mocked ES)."""

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from src.rag.retrieval import retrieve_articles, retrieve_ticket_kbs


@pytest.mark.asyncio
async def test_retrieve_articles_requires_query():
    with pytest.raises(HTTPException) as exc:
        await retrieve_articles(None, es_client=MagicMock())
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_retrieve_ticket_kbs_404(dummy_ticket):
    mock_es = MagicMock()
    mock_es.custom_query_articles.return_value = []
    with pytest.raises(HTTPException) as exc:
        await retrieve_ticket_kbs(dummy_ticket, es_client=mock_es)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_retrieve_ticket_kbs_ok(dummy_ticket, dummy_indexed_hits):
    mock_es = MagicMock()
    mock_es.custom_query_articles.return_value = dummy_indexed_hits
    out = await retrieve_ticket_kbs(dummy_ticket, es_client=mock_es)
    assert len(out) == 2
