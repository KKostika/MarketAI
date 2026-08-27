from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from typing import List

from app.core.database import get_session
from app.services.article_service import get_articles
from app.schemas.article import ArticleRead

router = APIRouter(prefix="/articles", tags=["Articles"])


@router.get("/{symbol}", response_model=List[ArticleRead])
def list_articles(symbol: str, session: Session = Depends(get_session)):
    """
    It generates and returns a list of articles related to the given stock symbol.

    Behavior implemented:
    - Validate the symbol input.
    - Fetch articles via get_articles(session, symbol).
    - Normalize and return a list of ArticleRead objects (or an empty list on failure).
    - Catch and log exceptions and return appropriate HTTP errors.
    """
    if not symbol or not isinstance(symbol, str):
        raise HTTPException(status_code=400, detail="Invalid symbol")

    try:
        articles = get_articles(session, symbol)
    except Exception as exc:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Failed to fetch articles") from exc

    # Defensive normalization: ensure a list is returned
    if articles is None:
        return []
    if not isinstance(articles, (list, tuple)):
        return [articles]

    return list(articles)
