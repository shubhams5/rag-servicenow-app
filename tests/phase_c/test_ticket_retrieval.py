"""Phase C: ticket query + ES query body (mocked client)."""

from unittest.mock import MagicMock

from src.rag.kb_fields import LEXICAL_SEARCH_FIELDS
from src.rag.ticket_retrieval import (
    build_related_kbs_query,
    build_ticket_query_text,
    get_related_kbs,
)


def test_build_ticket_query_text(dummy_ticket):
    text = build_ticket_query_text(dummy_ticket)
    assert "VPN disconnects" in text
    assert "Category: Network" in text
    assert "CI: DUMMY-LAPTOP-1" in text


def test_build_related_kbs_query_uses_indexed_fields():
    body = build_related_kbs_query("dummy vpn issue", top_k=3)
    assert body["size"] == 3
    multi = next(
        clause["multi_match"]
        for clause in body["query"]["bool"]["should"]
        if "multi_match" in clause
    )
    assert multi["fields"] == list(LEXICAL_SEARCH_FIELDS)
    assert "chunk_content^2" not in multi["fields"]


def test_get_related_kbs_uses_injected_client(dummy_ticket, dummy_indexed_hits):
    mock_es = MagicMock()
    mock_es.custom_query_articles.return_value = dummy_indexed_hits
    results = get_related_kbs(dummy_ticket, top_k=2, es_client=mock_es)
    assert results == dummy_indexed_hits
    mock_es.custom_query_articles.assert_called_once()
    sent = mock_es.custom_query_articles.call_args[0][0]
    assert sent["size"] == 2


def test_get_related_kbs_empty_ticket_text():
    mock_es = MagicMock()
    assert get_related_kbs({}, es_client=mock_es) == []
    mock_es.custom_query_articles.assert_not_called()
