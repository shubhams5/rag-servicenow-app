"""Phase C: chunking step + document id uniqueness (no ELSER/ES calls)."""

from unittest.mock import MagicMock, patch

from src.embeddings.chunk_and_embed import chunk_text
from src.rag.kb_fields import make_document_id
from src.storage.elasticsearch import ElasticsearchClient


def test_chunk_text_terminates_when_overlap_ge_size():
    words = " ".join(f"w{i}" for i in range(30))
    chunks = chunk_text(words, chunk_size=10, chunk_overlap=10)
    assert len(chunks) >= 1
    assert len(chunks) < 50  # would explode / hang if step were 0


def test_bulk_index_uses_doc_id(monkeypatch):
    client = ElasticsearchClient.__new__(ElasticsearchClient)
    client.index_name = "articles_test"
    client.client = MagicMock()

    captured = {}

    def fake_bulk(es, actions, request_timeout=60):
        captured["actions"] = list(actions)
        return (len(captured["actions"]), [])

    monkeypatch.setattr("src.storage.elasticsearch.bulk", fake_bulk)

    chunks = [
        {
            "sys_id": "sys-a",
            "chunk_no": "1_Same_1_0",
            "doc_id": make_document_id("sys-a", "1_Same_1_0"),
            "chunk": "a",
        },
        {
            "sys_id": "sys-b",
            "chunk_no": "1_Same_1_0",
            "doc_id": make_document_id("sys-b", "1_Same_1_0"),
            "chunk": "b",
        },
    ]
    client.bulk_index_articles(chunks)
    ids = [a["_id"] for a in captured["actions"]]
    assert ids[0] != ids[1]
    assert ids[0] == make_document_id("sys-a", "1_Same_1_0")


def test_scheduler_imports_src_run_pipeline():
    text = open("src/run_scheduler.py", encoding="utf-8").read()
    assert "from src.run_pipeline import main" in text
    assert "from run_pipeline import main" not in text
