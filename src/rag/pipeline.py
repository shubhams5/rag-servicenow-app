import logging

from fastapi import APIRouter, HTTPException

from src.rag.kb_fields import to_llm_hit, to_related_article
from src.rag.retrieval import retrieve_ticket_kbs

router = APIRouter()
logger = logging.getLogger("rag_pipeline")


def filter_articles_by_tags(articles, query):
    query_terms = set(query.lower().split())
    filtered = []
    for a in articles:
        tags = set([t.lower() for t in a.get("tags", []) or []])
        if tags & query_terms:
            filtered.append(a)
    logger.info("Filtered articles by tags: %s found", len(filtered))
    return filtered if filtered else articles


def rerank_articles_by_keyword(articles, query):
    query_terms = set(query.lower().split())
    scored = []
    for a in articles:
        tags = set([t.lower() for t in a.get("tags", []) or []])
        score = len(tags & query_terms)
        scored.append((score, a))
    scored.sort(key=lambda item: item[0], reverse=True)
    reranked = [a for score, a in scored if score > 0]
    logger.info("Reranked articles by keyword: %s found", len(reranked))
    return reranked if reranked else [a for score, a in scored]


async def rag_ticket_pipeline(ticket: dict, generate_fn=None):
    """Run retrieval + LLM for a ticket dict. Used by FastAPI `/rag`.

    generate_fn: optional injectable for tests (avoids loading transformers).
    """
    ticket_number = (ticket or {}).get("number", "")
    logger.info("Received ticket number=%s", ticket_number or "(none)")
    if not ticket:
        logger.error("No ticket data provided")
        raise HTTPException(status_code=400, detail="Ticket data is required")

    articles = await retrieve_ticket_kbs(ticket)
    logger.info("Retrieved %s KB articles for ticket", len(articles) if articles else 0)

    if not articles:
        logger.warning("No related KBs found")
        raise HTTPException(status_code=404, detail="No related KBs found")

    query = ticket.get("short_description") or ""
    filtered_articles = filter_articles_by_tags(articles, query)
    reranked_articles = rerank_articles_by_keyword(filtered_articles, query)

    kb_hits = [to_llm_hit(a) for a in reranked_articles]
    logger.info("Passing %s KB articles to LLM", len(kb_hits))
    if generate_fn is None:
        from src.generation.llm import generate_solution as generate_fn
    llm_response = generate_fn(ticket, kb_hits)

    related_articles = [to_related_article(a) for a in reranked_articles]
    logger.info("Returning %s related articles", len(related_articles))
    return {"recommended_solution": llm_response, "related_articles": related_articles}
