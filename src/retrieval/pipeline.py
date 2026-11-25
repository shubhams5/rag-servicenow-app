from src.rag.kb_fields import to_related_article
from src.storage.elasticsearch import ElasticsearchClient


def retrieve_solutions_for_ticket(ticket_description: str, top_n: int = 5, es_client=None):
    client = es_client if es_client is not None else ElasticsearchClient()
    results = client.semantic_query_articles(
        ticket_description, field="chunk_semantic", size=top_n
    )

    if not results:
        return {"recommended_solution": "No solution found.", "related_articles": []}

    first = to_related_article(results[0])
    recommended_solution = first["summary"] or "No solution text in top hit."
    related_articles = [to_related_article(r) for r in results]
    return {
        "recommended_solution": recommended_solution,
        "related_articles": related_articles,
    }
