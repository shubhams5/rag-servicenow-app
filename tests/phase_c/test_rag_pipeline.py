"""Phase C: RAG pipeline with mocked retrieval + LLM (no live keys)."""

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from src.rag.pipeline import (
    filter_articles_by_tags,
    rag_ticket_pipeline,
    rerank_articles_by_keyword,
)


def test_filter_and_rerank(dummy_indexed_hits):
    filtered = filter_articles_by_tags(dummy_indexed_hits, "vpn wifi")
    assert filtered
    reranked = rerank_articles_by_keyword(dummy_indexed_hits, "vpn")
    assert reranked[0]["title"] == "Dummy VPN Troubleshooting"


@pytest.mark.asyncio
async def test_rag_ticket_pipeline_success(dummy_ticket, dummy_indexed_hits, monkeypatch):
    async def fake_retrieve(ticket):
        return dummy_indexed_hits

    monkeypatch.setattr("src.rag.pipeline.retrieve_ticket_kbs", fake_retrieve)
    fake_llm = MagicMock(return_value="Dummy recommended steps")

    result = await rag_ticket_pipeline(dummy_ticket, generate_fn=fake_llm)
    assert result["recommended_solution"] == "Dummy recommended steps"
    assert result["related_articles"]
    assert result["related_articles"][0]["summary"]
    fake_llm.assert_called_once()
    kb_hits = fake_llm.call_args[0][1]
    assert kb_hits[0]["body"]


@pytest.mark.asyncio
async def test_rag_ticket_pipeline_404(monkeypatch):
    async def fake_retrieve(ticket):
        raise HTTPException(status_code=404, detail="No related KBs found")

    monkeypatch.setattr("src.rag.pipeline.retrieve_ticket_kbs", fake_retrieve)
    with pytest.raises(HTTPException) as exc:
        await rag_ticket_pipeline(
            {"number": "INC0", "short_description": "dummy nothing"},
            generate_fn=MagicMock(),
        )
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_rag_ticket_pipeline_requires_ticket():
    with pytest.raises(HTTPException) as exc:
        await rag_ticket_pipeline({}, generate_fn=MagicMock())
    assert exc.value.status_code == 400
