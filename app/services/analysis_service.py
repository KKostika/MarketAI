from __future__ import annotations
import logging
from typing import Any, Dict, List
from sqlmodel import Session
from datetime import datetime

from app.agents.agent_loop import run_agent
from app.schemas.stock import StockHistoryRequest
from app.services.stock_service import get_stock_price, get_stock_history, get_earnings
from app.services.article_service import get_articles

logger = logging.getLogger(__name__)


def _serialize_history(raw_history: List[Any]) -> List[Dict[str, Any]]:
    """Convert ORM history objects to plain dicts suitable for the agent."""
    out: List[Dict[str, Any]] = []
    for h in raw_history:
        try:
            date = h.date.isoformat() if hasattr(h.date, "isoformat") else str(getattr(h, "date", ""))
        except Exception:
            date = str(getattr(h, "date", ""))
        out.append({
            "date": date,
            "open": getattr(h, "open", None),
            "close": getattr(h, "close", None),
            "high": getattr(h, "high", None),
            "low": getattr(h, "low", None),
            "volume": getattr(h, "volume", None),
        })
    return out


def _serialize_articles(raw_articles: List[Any]) -> List[Dict[str, Any]]:
    """Convert ORM article objects to plain dicts suitable for the agent."""
    news_list: List[Dict[str, Any]] = []
    for a in raw_articles:
        try:
            published_at = (
                a.published_at.isoformat()
                if hasattr(a, "published_at") and hasattr(a.published_at, "isoformat")
                else str(getattr(a, "published_at", ""))
            )
        except Exception:
            published_at = str(getattr(a, "published_at", ""))
        news_list.append({
            "id": getattr(a, "id", None),
            "title": getattr(a, "title", ""),
            "url": getattr(a, "url", ""),
            "source": getattr(a, "source", ""),
            "published_at": published_at,
            "content": getattr(a, "content", "") or ""
        })
    return news_list


def generate_full_analysis(session: Session, symbol: str, user_language: str) -> dict:
    """
    Generate a full stock analysis for `symbol`.

    Steps
    - fetch current price
    - fetch recent price history
    - fetch earnings
    - fetch recent articles
    - call the LLM agent with aggregated data

    Returns a dict with the agent response or an empty dict on failure.
    """
    # Validate inputs early
    if not symbol or not isinstance(symbol, str):
        logger.error("generate_full_analysis called with invalid symbol: %r", symbol)
        return {}

    price = None
    try:
        price = get_stock_price(symbol)
    except Exception as exc:
        logger.warning("get_stock_price failed for %s: %s", symbol, exc)

    
    raw_history = []
    try:
        history_request = StockHistoryRequest(symbol=symbol, period="1mo")
        raw_history = get_stock_history(session, history_request) or []
    except Exception as exc:
        logger.warning("get_stock_history failed for %s: %s", symbol, exc)

    history = _serialize_history(raw_history)

    
    earnings = []
    try:
        earnings = get_earnings(symbol) or []
    except Exception as exc:
        logger.info("get_earnings failed for %s: %s", symbol, exc)

    raw_articles = []
    try:
        raw_articles = get_articles(session, symbol) or []
    except Exception as exc:
        logger.warning("get_articles failed for %s: %s", symbol, exc)

    news_list = _serialize_articles(raw_articles)

    stock_data = {
        "symbol": symbol,
        "price": price,
        "history": history,
        "earnings": earnings,
        "news": news_list
    }

    # 6. Call agent (structured JSON expected)
    try:
        agent_response = run_agent(user_language=user_language, stock_data=stock_data)
    except Exception as exc:
        logger.error("run_agent failed for %s: %s", symbol, exc, exc_info=True)
        agent_response = {}

    return agent_response
