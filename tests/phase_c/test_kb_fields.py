"""Phase C: indexed field contract helpers."""

from src.rag.kb_fields import (
    LEXICAL_SEARCH_FIELDS,
    chunk_body,
    make_document_id,
    normalize_kb_document,
    safe_chunk_step,
    to_llm_hit,
    to_related_article,
)


def test_chunk_body_prefers_indexed_chunk(dummy_indexed_hit):
    assert chunk_body(dummy_indexed_hit).startswith("Restart the dummy")


def test_chunk_body_falls_back_to_legacy_summary():
    assert chunk_body({"summary": "legacy summary only"}) == "legacy summary only"
    assert chunk_body({"body": "legacy body"}) == "legacy body"


def test_normalize_fills_aliases(dummy_indexed_hit):
    norm = normalize_kb_document(dummy_indexed_hit)
    assert norm["title"] == "Dummy VPN Troubleshooting"
    assert norm["chunk"]
    assert norm["body"] == norm["chunk"]
    assert norm["summary"] == norm["chunk"]
    assert "vpn" in norm["tags"]


def test_to_llm_and_related(dummy_indexed_hit):
    hit = to_llm_hit(dummy_indexed_hit)
    assert hit["body"]
    assert hit["title"]
    related = to_related_article(dummy_indexed_hit)
    assert "summary" in related
    assert related["summary"]
    # No KeyError path: missing summary on raw doc still works
    raw = {"title": "T", "chunk": "C", "tags": []}
    assert to_related_article(raw)["summary"] == "C"


def test_make_document_id_unique_across_articles():
    a = make_document_id("sys-a", "1_SameTitle_1_0")
    b = make_document_id("sys-b", "1_SameTitle_1_0")
    assert a != b
    assert a.startswith("sys-a__")


def test_lexical_fields_match_index_names():
    joined = " ".join(LEXICAL_SEARCH_FIELDS)
    assert "chunk^2" in joined or "chunk" in joined
    assert "title" in joined
    assert "chunk_content" not in joined
    assert "meta_data.title" not in joined
    assert "keywords" not in joined  # old wrong field


def test_safe_chunk_step_never_zero():
    assert safe_chunk_step(512, 50) == 462
    assert safe_chunk_step(100, 100) >= 1
    assert safe_chunk_step(100, 200) >= 1
    assert safe_chunk_step(0, 0) >= 1
