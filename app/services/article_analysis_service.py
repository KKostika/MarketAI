from __future__ import annotations
import logging
from datetime import datetime
from typing import Optional
from sqlmodel import Session, select

from app.models.article_analysis import ArticleAnalysis
from app.models.article import Article

logger = logging.getLogger(__name__)


def get_analysis_by_article_id(
    session: Session,
    article_id: int
) -> Optional[ArticleAnalysis]:
    """
    Retrieve an ArticleAnalysis row by the related article id.

    Returns the ArticleAnalysis instance or None if not found.
    """
    statement = select(ArticleAnalysis).where(
        ArticleAnalysis.article_id == article_id
    )
    try:
        return session.exec(statement).first()
    except Exception:
        logger.exception("Failed to query ArticleAnalysis for article_id=%s", article_id)
        return None


def save_article_analysis(
    session: Session,
    article_id: int,
    sentiment_score: float,
    summary: str
) -> ArticleAnalysis:
    """
    Create and persist a new ArticleAnalysis record.

    Commits the transaction and refreshes the instance before returning it.
    On failure the transaction is rolled back and the exception is re-raised.
    """
    analysis = ArticleAnalysis(
        article_id=article_id,
        sentiment_score=sentiment_score,
        summary=summary,
        created_at=datetime.utcnow()
    )

    session.add(analysis)
    try:
        session.commit()
        session.refresh(analysis)
        return analysis
    except Exception:
        session.rollback()
        logger.exception(
            "Failed to save ArticleAnalysis for article_id=%s (sentiment=%s)",
            article_id,
            sentiment_score
        )
        raise


def get_or_create_article_analysis(
    session: Session,
    article: Article,
    sentiment_score: float,
    summary: str
) -> ArticleAnalysis:
    """
    Return an existing ArticleAnalysis for the given article, or create one.

    This is safe to call concurrently but does not implement explicit locking;
    callers that require strict uniqueness under concurrency should handle retries
    or use DB-level constraints and handle IntegrityError accordingly.
    """
    existing = get_analysis_by_article_id(session, article.id)
    if existing:
        return existing

    return save_article_analysis(
        session=session,
        article_id=article.id,
        sentiment_score=sentiment_score,
        summary=summary
    )


def analysis_to_schema(analysis: ArticleAnalysis) -> dict:
    """
    Convert an ArticleAnalysis DB model to a plain dict suitable for JSON responses.

    The returned dict uses ISO 8601 for the created_at timestamp.
    """
    created_at = getattr(analysis, "created_at", None)
    created_at_iso = created_at.isoformat() if created_at is not None else None

    return {
        "article_id": analysis.article_id,
        "sentiment_score": analysis.sentiment_score,
        "summary": analysis.summary,
        "created_at": created_at_iso
    }
