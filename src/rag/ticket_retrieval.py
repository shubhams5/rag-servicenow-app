from src.rag.exceptions import RetrievalError
from src.rag.kb_fields import ELSER_INFERENCE_ID, LEXICAL_SEARCH_FIELDS
from src.storage.elasticsearch import ElasticsearchClient

_elasticsearch_client = None


def _get_es_client():
    global _elasticsearch_client
    if _elasticsearch_client is None:
        _elasticsearch_client = ElasticsearchClient()
    return _elasticsearch_client


def build_ticket_query_text(ticket: dict) -> str:
    """Build a semantic query string from a ServiceNow ticket dict."""
    parts = []
    if ticket.get("short_description"):
        parts.append(ticket["short_description"])
    if ticket.get("description"):
        parts.append(ticket["description"])
    if ticket.get("category"):
        parts.append(f"Category: {ticket['category']}")
    if ticket.get("subcategory"):
        parts.append(f"Subcategory: {ticket['subcategory']}")
    if ticket.get("cmdb_ci"):
        parts.append(f"CI: {ticket['cmdb_ci']}")
    return "\n".join(parts)


def build_related_kbs_query(query_text: str, top_k: int = 5) -> dict:
    """ES query body for ticket → KB retrieval (lexical fields match indexed docs)."""
    return {
        "size": top_k,
        "query": {
            "bool": {
                "should": [
                    {
                        "sparse_vector": {
                            "field": "elser_chunk_content",
                            "inference_id": ELSER_INFERENCE_ID,
                            "query": query_text,
                            "boost": 1.0,
                        }
                    },
                    {
                        "sparse_vector": {
                            "field": "elser_title",
                            "inference_id": ELSER_INFERENCE_ID,
                            "query": query_text,
                            "boost": 1.1,
                        }
                    },
                    {
                        "sparse_vector": {
                            "field": "elser_keywords",
                            "inference_id": ELSER_INFERENCE_ID,
                            "query": query_text,
                            "boost": 1.2,
                        }
                    },
                    {
                        "multi_match": {
                            "query": query_text,
                            "fields": list(LEXICAL_SEARCH_FIELDS),
                            "type": "best_fields",
                        }
                    },
                ]
            }
        },
    }


def get_related_kbs(ticket: dict, top_k: int = 5, es_client=None) -> list:
    """
    Retrieve top_k related knowledge base articles for a given ticket.
    Pass es_client in tests to avoid a live Elasticsearch connection.
    """
    query_text = build_ticket_query_text(ticket)
    if not query_text.strip():
        return []
    query_body = build_related_kbs_query(query_text, top_k=top_k)
    client = es_client if es_client is not None else _get_es_client()
    try:
        return client.custom_query_articles(query_body)
    except Exception as error:
        raise RetrievalError("Elasticsearch query failed") from error
