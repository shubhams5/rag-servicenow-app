from typing import List, Optional

from fastapi import APIRouter, HTTPException

from src.rag.exceptions import RetrievalError
from src.rag.ticket_retrieval import get_related_kbs
from src.storage.elasticsearch import ElasticsearchClient
from src.types.article import KbChunk

router = APIRouter()
_elasticsearch_client = None


def _get_es_client():
    global _elasticsearch_client
    if _elasticsearch_client is None:
        _elasticsearch_client = ElasticsearchClient()
    return _elasticsearch_client


async def retrieve_articles(query: Optional[str], es_client=None):
    if not query:
        raise HTTPException(status_code=400, detail="Query parameter is required")
    client = es_client if es_client is not None else _get_es_client()
    try:
        return client.semantic_query_articles(
            query, field="chunk_semantic", size=3
        )
    except HTTPException:
        raise
    except RetrievalError as error:
        raise HTTPException(
            status_code=503, detail="Search backend unavailable"
        ) from error
    except Exception as error:
        raise HTTPException(
            status_code=503, detail="Search backend unavailable"
        ) from error


async def retrieve_ticket_kbs(ticket: dict, es_client=None) -> List[dict]:
    if not ticket:
        raise HTTPException(status_code=400, detail="Ticket data is required")
    try:
        articles = get_related_kbs(ticket, top_k=3, es_client=es_client)
        if not articles:
            raise HTTPException(status_code=404, detail="No related KBs found")
        return articles
    except HTTPException:
        raise
    except RetrievalError:
        raise HTTPException(status_code=503, detail="Search backend unavailable")
    except Exception as error:
        raise HTTPException(
            status_code=500, detail="An error occurred while retrieving ticket KBs"
        ) from error


@router.post("/retrieve", response_model=List[KbChunk])
async def retrieve_articles_route(query: str):
    return await retrieve_articles(query)


@router.post("/retrieve_ticket_kbs", response_model=List[KbChunk])
async def retrieve_ticket_kbs_route(ticket: dict):
    return await retrieve_ticket_kbs(ticket)
