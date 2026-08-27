from __future__ import annotations
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Any, Dict

import requests
from sqlmodel import Session, select

from app.models.stock import Stock
from app.models.stock_history import StockHistory
from app.schemas.stock import StockHistoryRequest
from app.schemas.stock_history import StockHistoryBase
from app.core.config import Settings

logger = logging.getLogger(__name__)
settings = Settings()


def get_or_create_stock(session: Session, symbol: str) -> Stock:
    """
    Return the Stock row for `symbol`, creating it if missing.

    Commits the new Stock and refreshes the instance before returning.
    """
    statement = select(Stock).where(Stock.symbol == symbol)
    try:
        stock = session.exec(statement).first()
    except Exception:
        logger.exception("DB query failed while looking up stock %s", symbol)
        raise

    if stock:
        return stock

    stock = Stock(symbol=symbol)
    session.add(stock)
    try:
        session.commit()
        session.refresh(stock)
        logger.info("Created new stock record for %s (id=%s)", symbol, stock.id)
        return stock
    except Exception:
        session.rollback()
        logger.exception("Failed to create stock record for %s", symbol)
        raise


def fetch_stock_history_from_api(symbol: str, period: str) -> List[Dict[str, Any]]:
    """
    Fetch daily adjusted time series from Alpha Vantage.

    Returns a list of dicts with keys: timestamp, open, close, high, low, volume.
    On error or missing data returns an empty list.
    """
    if not settings.STOCK_API_KEY:
        raise ValueError("STOCK_API_KEY is missing. Check your .env file.")

    url = (
        "https://www.alphavantage.co/query"
        f"?function=TIME_SERIES_DAILY_ADJUSTED"
        f"&symbol={symbol}"
        f"&apikey={settings.STOCK_API_KEY}"
    )

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        logger.warning("Stock API request failed for %s: %s", symbol, exc)
        return []
    except ValueError as exc:
        logger.warning("Stock API returned invalid JSON for %s: %s", symbol, exc)
        return []

    ts = data.get("Time Series (Daily)")
    if not isinstance(ts, dict):
        logger.debug("AlphaVantage response missing Time Series (Daily) for %s", symbol)
        return []

    results: List[Dict[str, Any]] = []
    for date_str, values in ts.items():
        try:
            results.append({
                "timestamp": date_str,
                "open": float(values.get("1. open", 0.0)),
                "close": float(values.get("4. close", 0.0)),
                "high": float(values.get("2. high", 0.0)),
                "low": float(values.get("3. low", 0.0)),
                "volume": int(values.get("6. volume", 0)),
            })
        except Exception:
            logger.debug("Skipping malformed time series entry for %s on %s", symbol, date_str, exc_info=True)
            continue

    results.sort(key=lambda x: x["timestamp"])
    return results


def filter_last_months(data: List[Dict[str, Any]], months: int) -> List[Dict[str, Any]]:
    """
    Keep only entries whose timestamp is within the last `months` months.

    Uses a 30-day month approximation for cutoff calculation.
    """
    cutoff = datetime.utcnow() - timedelta(days=months * 30)
    filtered: List[Dict[str, Any]] = []

    for item in data:
        ts = item.get("timestamp")
        if not ts:
            continue
        try:
            date = datetime.fromisoformat(ts)
        except Exception:
            try:
                date = datetime.fromisoformat(str(ts).split("T")[0])
            except Exception:
                logger.debug("Unable to parse timestamp %r", ts)
                continue

        if date >= cutoff:
            filtered.append(item)

    return filtered


def get_stock_history_last_months(session: Session, symbol: str, months: int = 6) -> List[StockHistoryBase]:
    """
    Fetch history from API for the full series, filter last `months` months,
    save to DB and return structured StockHistoryBase list.
    """
    stock = get_or_create_stock(session, symbol)

    api_data = fetch_stock_history_from_api(symbol, period="compact")
    if not api_data:
        return []

    filtered = filter_last_months(api_data, months)
    if filtered:
        try:
            save_stock_history(session, stock, filtered)
        except Exception:
            logger.exception("Failed to save filtered stock history for %s", symbol)

    return get_stock_history_from_db(session, stock.id)


def save_stock_history(session: Session, stock: Stock, data: List[Dict[str, Any]]) -> None:
    """
    Persist a list of daily OHLCV dicts into the DB.

    Deduplicates by (stock_id, date). Commits once at the end. Rolls back on failure.
    """
    if not data:
        return

    added = 0
    for item in data:
        ts = item.get("timestamp")
        if not ts:
            continue

        try:
            date = datetime.fromisoformat(ts)
        except Exception:
            try:
                date = datetime.fromisoformat(str(ts).split("T")[0])
            except Exception:
                logger.debug("Skipping entry with unparsable timestamp: %r", ts)
                continue

        try:
            existing = session.exec(
                select(StockHistory).where(
                    StockHistory.stock_id == stock.id,
                    StockHistory.date == date
                )
            ).first()
        except Exception:
            logger.exception("DB query failed during deduplication for stock_id=%s date=%s", stock.id, date)
            existing = None

        if existing:
            continue

        history = StockHistory(
            stock_id=stock.id,
            date=date,
            open=item.get("open"),
            close=item.get("close"),
            high=item.get("high"),
            low=item.get("low"),
            volume=item.get("volume"),
        )

        try:
            session.add(history)
            added += 1
        except Exception:
            logger.exception("Failed to add StockHistory for stock_id=%s date=%s", stock.id, date)
            continue

    if added == 0:
        return

    try:
        session.commit()
        logger.info("Saved %d new history rows for stock %s (id=%s)", added, stock.symbol, stock.id)
    except Exception:
        session.rollback()
        logger.exception("Failed to commit stock history for %s; rolled back", stock.symbol)
        raise


def get_stock_history_from_db(session: Session, stock_id: int) -> List[StockHistoryBase]:
    """
    Read stock history rows from DB and return a list of StockHistoryBase schemas.
    """
    try:
        statement = (
            select(StockHistory)
            .where(StockHistory.stock_id == stock_id)
            .order_by(StockHistory.date)
        )
        results = session.exec(statement).all()
    except Exception:
        logger.exception("Failed to query stock history for stock_id=%s", stock_id)
        return []

    out: List[StockHistoryBase] = []
    for r in results:
        out.append(
            StockHistoryBase(
                date=r.date,
                open=r.open,
                close=r.close,
                high=r.high,
                low=r.low,
                volume=r.volume,
            )
        )
    return out


def get_stock_history(session: Session, request: StockHistoryRequest) -> List[StockHistoryBase]:
    """
    Main entry point to obtain stock history for a symbol and period.

    Flow:
    1. Ensure stock exists
    2. Try DB first
    3. If missing, fetch from API and save
    4. Return DB results
    """
    stock = get_or_create_stock(session, request.symbol)

    db_data = get_stock_history_from_db(session, stock.id)
    if db_data:
        return db_data

    api_data = fetch_stock_history_from_api(request.symbol, request.period)
    if not api_data:
        return []

    try:
        save_stock_history(session, stock, api_data)
    except Exception:
        logger.exception("Failed to save stock history for %s", request.symbol)
        return get_stock_history_from_db(session, stock.id)

    return get_stock_history_from_db(session, stock.id)


def get_stock_price(symbol: str) -> Optional[float]:
    """
    Fetch current stock price via Alpha Vantage GLOBAL_QUOTE.

    Returns float price or None on error.
    """
    if not settings.STOCK_API_KEY:
        raise ValueError("STOCK_API_KEY is missing. Check your .env file.")

    url = (
        "https://www.alphavantage.co/query"
        f"?function=GLOBAL_QUOTE"
        f"&symbol={symbol}"
        f"&apikey={settings.STOCK_API_KEY}"
    )

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException:
        logger.warning("Failed to fetch global quote for %s", symbol)
        return None
    except ValueError:
        logger.warning("Invalid JSON in global quote response for %s", symbol)
        return None

    quote = data.get("Global Quote", {})
    price = quote.get("05. price")
    if not price:
        return None

    try:
        return float(price)
    except Exception:
        logger.debug("Unable to parse price %r for %s", price, symbol)
        return None


def get_earnings(symbol: str) -> List[Dict[str, Any]]:
    """
    Fetch recent earnings (quarterly) from Alpha Vantage.

    Returns a list of dicts for the last quarters or an empty list on error.
    """
    if not settings.STOCK_API_KEY:
        raise ValueError("STOCK_API_KEY is missing. Check your .env file.")

    url = (
        "https://www.alphavantage.co/query"
        f"?function=EARNINGS"
        f"&symbol={symbol}"
        f"&apikey={settings.STOCK_API_KEY}"
    )

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException:
        logger.warning("Failed to fetch earnings for %s", symbol)
        return []
    except ValueError:
        logger.warning("Invalid JSON in earnings response for %s", symbol)
        return []

    quarterly = data.get("quarterlyEarnings", [])
    if not isinstance(quarterly, list):
        return []

    results: List[Dict[str, Any]] = []
    for item in quarterly[:4]:
        results.append({
            "fiscalDateEnding": item.get("fiscalDateEnding"),
            "reportedEPS": item.get("reportedEPS"),
            "surprise": item.get("surprise"),
            "surprisePercentage": item.get("surprisePercentage"),
        })

    return results
