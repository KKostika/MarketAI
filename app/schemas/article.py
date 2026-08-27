from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel


class ArticleBase(BaseModel):
    title: str
    url: str
    source: str


class ArticleCreate(ArticleBase):
    published_at: datetime
    content: str | None = None


class ArticleRead(ArticleBase):
    id: int
    published_at: datetime
    content: str | None = None

    model_config = {
        "from_attributes": True
    }
