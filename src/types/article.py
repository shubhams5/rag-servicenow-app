from typing import List, Optional

from pydantic import BaseModel, Field


class KbChunk(BaseModel):
    """Shape aligned with documents produced by chunk_and_embed."""

    title: str = ""
    chunk: str = ""
    chunk_semantic: str = ""
    tags: Optional[List[str]] = None
    chunk_no: str = ""
    article_number: str = ""
    sys_id: str = ""
    type: str = ""
    summary: str = ""  # normalized alias
    body: str = ""  # normalized alias


class Article(BaseModel):
    """Legacy response model — prefer KbChunk for indexed documents."""

    id: str = ""
    title: str = ""
    content: str = ""
    created_at: str = ""
    updated_at: str = ""
    tags: Optional[List[str]] = None


class ArticleIngest(BaseModel):
    title: str
    content: str
    tags: Optional[List[str]] = None


class ArticleResponse(BaseModel):
    articles: List[Article] = Field(default_factory=list)
