from __future__ import annotations
import logging
from datetime import datetime
from typing import List, Dict, Any

import requests
from sqlmodel import Session, select

from app.models.article import Article
from app.schemas.article import ArticleRead
from app.core.config import Settings

logger = logging.getLogger(__name__)
settings = Settings()


def fetch_articles_from_api(symbol: str, timeout: int = 10) -> List[Dict[str, Any]]:
    """
    Fetch raw articles from the configured external news API for a symbol.

    Returns a list of dicts (possibly empty) or raises ValueError if configuration is missing.
    Network errors are caught and an empty list is returned.
    """
    if not settings.NEWS_API_KEY:
        raise ValueError("NEWS_API_KEY is missing. Check your .env file.")

    url = f"{settings.NEWS_API_URL}?q={symbol}&apikey={settings.NEWS_API_KEY}"
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        logger.warning("News API request failed for %s: %s", symbol, exc)
        return []
    except ValueError as exc:
        # JSON decode error
        logger.warning("News API returned invalid JSON for %s: %s", symbol, exc)
        return []

    if isinstance(data, dict):
        for key in ("articles", "data", "results"):
            if key in data:
                return data.get(key) or []
        return [data]

    if isinstance(data, list):
        return data

    return []


def _parse_published_at(raw_date: Any) -> datetime:
    """
    Robust parsing for published_at fields.
    Falls back to current UTC time on failure.
    """
    if not raw_date:
        return datetime.utcnow()

    if isinstance(raw_date, datetime):
        return raw_date

    try:
        return datetime.fromisoformat(str(raw_date))
    except Exception:
        pass

    for fmt in ("%a, %d %b %Y %H:%M:%S %Z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(str(raw_date), fmt)
        except Exception:
            continue

    logger.debug("Could not parse published_at=%r, using utcnow", raw_date)
    return datetime.utcnow()


def save_articles(session: Session, symbol: str, articles: List[Dict[str, Any]]) -> None:
    """
    Persist a list of normalized article dicts into the database.

    Deduplicates by URL. Commits once at the end. On failure rolls back and logs.
    """
    if not articles:
        return

    added = 0
    for item in articles:
        if not item or not isinstance(item, dict):
            continue

        title = item.get("title")
        url = item.get("url")
        if not title or not url:
            continue

        try:
            existing = session.exec(select(Article).where(Article.url == url)).first()
        except Exception:
            logger.exception("DB query failed during deduplication for url=%s", url)
            existing = None

        if existing:
            continue

        raw_date = (
            item.get("published_at")
            or item.get("publishedAt")
            or item.get("date")
            or item.get("pubDate")
        )
        published_at = _parse_published_at(raw_date)

        source = item.get("source")
        if isinstance(source, dict):
            source = source.get("name", "unknown")
        elif not isinstance(source, str):
            source = "unknown"

        article = Article(
            title=title,
            url=url,
            source=source,
            published_at=published_at,
            content=item.get("content") or item.get("description") or "",
            stock_symbol=symbol
        )

        try:
            session.add(article)
            added += 1
        except Exception:
            logger.exception("Failed to add Article object for url=%s", url)

    if added == 0:
        return

    try:
        session.commit()
        logger.info("Saved %d new articles for %s", added, symbol)
    except Exception:
        session.rollback()
        logger.exception("Failed to commit articles for %s; rolled back", symbol)
        raise


def get_articles_from_db(session: Session, symbol: str) -> List[ArticleRead]:
    """
    Retrieve articles for a symbol from the DB ordered by published_at desc.

    Returns a list of ArticleRead schemas.
    """
    try:
        statement = (
            select(Article)
            .where(Article.stock_symbol == symbol)
            .order_by(Article.published_at.desc())
        )
        results = session.exec(statement).all()
    except Exception:
        logger.exception("Failed to query articles from DB for %s", symbol)
        return []

    out: List[ArticleRead] = []
    for a in results:
        published_iso = a.published_at.isoformat() if getattr(a, "published_at", None) else None
        out.append(
            ArticleRead(
                id=a.id,
                title=a.title,
                url=a.url,
                source=a.source,
                published_at=published_iso,
                content=a.content
            )
        )
    return out


def get_articles(session: Session, symbol: str) -> List[ArticleRead]:
    """
    Main entry point to obtain articles for a symbol.

    Flow:
    1. Try DB first
    2. If none, fetch from external API
    3. Save to DB (deduplicated)
    4. Return DB results

    Returns an empty list on any recoverable failure.
    """
    # 1. Try DB first
    db_articles = get_articles_from_db(session, symbol)
    if db_articles:
        return db_articles

    # 2. Otherwise fetch from API
    try:
        api_data = fetch_articles_from_api(symbol)
    except ValueError as exc:
        logger.error("Configuration error when fetching articles for %s: %s", symbol, exc)
        return []
    except Exception:
        logger.exception("Unexpected error when fetching articles for %s", symbol)
        return []

    if not api_data:
        return []

    # 3. Save to DB
    try:
        save_articles(session, symbol, api_data)
    except Exception:
        # save_articles already logs and rolls back; return DB fallback (likely empty)
        logger.warning("Saving articles failed for %s; returning DB results (may be empty)", symbol)

    # 4. Return structured data
    return get_articles_from_db(session, symbol)
