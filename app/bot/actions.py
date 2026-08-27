import json
import traceback
from typing import Any, Dict, List, Optional

import requests
from anyio.to_thread import run_sync
from app.core.config import Settings

from app.bot.sender import send_message, send_progressive, send_typing
from app.bot.keyboards import send_action_keyboard
from app.agents.tools.news import fetch_news
from app.agents.tools.earnings import fetch_earnings
from app.agents.agent_loop import run_agent

settings = Settings()
AV_KEY = settings.STOCK_API_KEY


async def quick_price(symbol: str) -> str:
    """
    It generates a short price summary for the given stock.

    Behavior:
    - Calls AlphaVantage synchronously in a thread to avoid blocking the event loop.
    - Returns a formatted string or a friendly error message.
    """
    if not symbol or not isinstance(symbol, str):
        return "⚠️ Invalid symbol."

    def _fetch() -> Dict[str, Any]:
        url = "https://www.alphavantage.co/query"
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol,
            "apikey": AV_KEY
        }
        resp = requests.get(url, params=params, timeout=10)
        return resp.json()

    try:
        data = await run_sync(_fetch)
    except Exception:
        traceback.print_exc()
        return f"⚠️ Πρόβλημα κατά την ανάκτηση τιμής για {symbol}."

    try:
        if "Global Quote" not in data:
            return f"⚠️ Δεν βρήκα τιμή για {symbol}."

        quote = data["Global Quote"]
        price = quote.get("05. price", "—")
        change = quote.get("09. change", "—")
        change_pct = quote.get("10. change percent", "—")

        return (
            f"📈 *{symbol}*\n"
            f"Τρέχουσα τιμή: *${price}*\n"
            f"Μεταβολή: {change} ({change_pct})"
        )
    except Exception:
        traceback.print_exc()
        return f"⚠️ Σφάλμα στην επεξεργασία της τιμής για {symbol}."


async def send_news(chat_id: int, symbol: str):
    """
    It generates and sends a short list of news articles for a stock.

    Behavior:
    - Supports async or sync fetch_news implementations.
    - Sends a progressive message with up to several articles.
    - Handles errors gracefully and notifies the user.
    """
    if not symbol:
        return send_message(chat_id, "Δεν έχω σύμβολο. Πες μου π.χ. TSLA.")

    try:
        if callable(getattr(fetch_news, "__call__", None)) and getattr(fetch_news, "__name__", "") == "fetch_news":
            # try awaiting if it's async
            try:
                articles = await fetch_news(symbol)
            except TypeError:
                # sync function
                articles = await run_sync(fetch_news, symbol)
        else:
            # fallback: run in thread
            articles = await run_sync(fetch_news, symbol)
    except Exception:
        traceback.print_exc()
        return send_message(chat_id, "Συγγνώμη, πρόβλημα κατά την ανάκτηση ειδήσεων.")

    if not articles:
        return send_message(chat_id, "Δεν βρήκα νέα για αυτή τη μετοχή.")

    try:
        text = "📰 *Τελευταία Νέα*\n\n"
        for a in articles:
            title = a.get("title") if isinstance(a, dict) else getattr(a, "title", "")
            summary = a.get("summary") if isinstance(a, dict) else getattr(a, "summary", "")
            url = a.get("url") if isinstance(a, dict) else getattr(a, "url", "")
            text += f"• *{title}*\n{summary}\n{url}\n\n"

        await send_progressive(chat_id, text)
    except Exception:
        traceback.print_exc()
        return send_message(chat_id, "Σφάλμα κατά την αποστολή των ειδήσεων.")


async def send_earnings(chat_id: int, symbol: str):
    """
    It generates and sends the next/last earnings info for a stock.

    Behavior:
    - Supports async or sync fetch_earnings implementations.
    - Formats and sends a concise message or an error notice.
    """
    if not symbol:
        return send_message(chat_id, "Δεν έχω σύμβολο. Πες μου π.χ. AAPL.")

    try:
        try:
            earnings = await fetch_earnings(symbol)
        except TypeError:
            earnings = await run_sync(fetch_earnings, symbol)
    except Exception:
        traceback.print_exc()
        return send_message(chat_id, "Συγγνώμη, πρόβλημα κατά την ανάκτηση των earnings.")

    if not earnings:
        return send_message(chat_id, "Δεν βρήκα earnings για αυτή τη μετοχή.")

    try:
        date = earnings.get("date") or earnings.get("report_date") or "N/A"
        prev_eps = earnings.get("previous_eps") or earnings.get("prev_eps") or "N/A"
        consensus = earnings.get("consensus_eps") or earnings.get("consensus") or "N/A"

        text = (
            f"📅 *Earnings για {symbol}*\n\n"
            f"Ημερομηνία: {date}\n"
            f"Προηγούμενο EPS: {prev_eps}\n"
            f"Consensus EPS: {consensus}\n"
        )
        send_message(chat_id, text)
    except Exception:
        traceback.print_exc()
        return send_message(chat_id, "Σφάλμα κατά την αποστολή των earnings.")


async def send_full_analysis(chat_id: int, symbol: str):
    """
    It generates and sends a full analysis using the agent.

    Behavior:
    - Sends typing indicator, runs the agent in a thread if blocking, and streams the result.
    - Handles errors and notifies the user gracefully.
    """
    if not symbol:
        return send_message(chat_id, "Δεν έχω σύμβολο. Πες μου π.χ. NVDA.")

    try:
        await send_typing(chat_id)
    except Exception:
        # best-effort typing indicator; ignore failures
        pass

    try:
        try:
            result = await run_sync(run_agent, {"symbol": symbol})
        except TypeError:
            # if run_agent is async, call it directly
            result = await run_agent({"symbol": symbol})
    except Exception:
        traceback.print_exc()
        return send_progressive(chat_id, "Συγγνώμη, προέκυψε σφάλμα κατά την παραγωγή της ανάλυσης.")

    try:
        if isinstance(result, dict):
            summary = json.dumps(result, ensure_ascii=False, indent=2)
            await send_progressive(chat_id, f"🔎 *Full analysis for {symbol}*\n\n{summary}")
        else:
            await send_progressive(chat_id, str(result))
    except Exception:
        traceback.print_exc()
        try:
            await send_progressive(chat_id, "Συγγνώμη, σφάλμα κατά την αποστολή του αποτελέσματος.")
        except Exception:
            pass
