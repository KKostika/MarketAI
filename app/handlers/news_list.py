import json
import asyncio
import traceback
from typing import Any, List, Optional

from sqlmodel import Session
from app.db.engine import engine
from app.bot.sender import generate_dynamic_prompt, send_progressive
from app.services.article_service import get_articles

last_bot_message: dict[int, str] = {}

async def handle_news_list(chat_id: int, symbol: str, user_text: str = "") -> None:
    """
    It generates and sends a concise list of recent news articles for a stock symbol.

    Behavior implemented:
    - Validate the symbol input.
    - Fetch articles from the service; if the service is blocking, run it in a thread executor.
    - Normalize results to a list of article-like objects/dicts.
    - Send up to three articles as progressive messages with safe formatting.
    - Save the shown list for contextual follow-ups and produce a dynamic closing prompt.
    - Log full tracebacks and notify the user gracefully on error.
    """
    if not symbol or not isinstance(symbol, str):
        try:
            await send_progressive(chat_id, "Invalid symbol provided.")
        except Exception:
            pass
        return

    try:
        if asyncio.iscoroutinefunction(get_articles):
            articles = await get_articles(None, symbol)
        else:
            def _call_with_session() -> Any:
                with Session(engine) as session:
                    return get_articles(session, symbol)
            loop = asyncio.get_running_loop()
            articles = await loop.run_in_executor(None, _call_with_session)


        if not articles:
            await send_progressive(chat_id, f"No recent news found for *{symbol}* 📰")
            return

        if isinstance(articles, dict):
            for key in ("articles", "data", "results"):
                if key in articles and isinstance(articles[key], (list, tuple)):
                    articles = articles[key]
                    break

        if not isinstance(articles, (list, tuple)):
            articles = [articles]

        # Keep top 3
        top: List[Any] = articles[:3]

        # Header
        await send_progressive(chat_id, f"📰 *Latest news for {symbol}:*")

        shown_news: List[str] = []

        for a in top:
            def _get(attr: str, default: str = "") -> str:
                if isinstance(a, dict):
                    return a.get(attr, default) or default
                return getattr(a, attr, default) or default

            # Date formatting
            try:
                published = _get("published_at") or _get("publishedAt") or _get("date") or ""
                if isinstance(published, str) and published:
                    date = published[:10]
                else:
                    date = str(published)[:10] if published else "N/A"
            except Exception:
                date = "N/A"

            # Short summary: first sentence of content or description
            content = _get("content") or _get("description") or ""
            short_summary = ""
            if content:
                parts = content.split(".")
                if parts:
                    short_summary = parts[0].strip()
                    if short_summary:
                        short_summary += "."

            url = _get("url", "")
            source = _get("source", "")
            title = _get("title", "Untitled")

            msg = (
                f"• *{title}*\n"
                f"  _{source}_ — {date}\n"
                f"  {short_summary}\n"
                f"  {url}"
            )

            shown_news.append(msg)
            await send_progressive(chat_id, msg)

        # Save last bot message for contextual follow-up
        last_bot_message[chat_id] = "\n".join(shown_news)

        closing_context = f"""
The assistant just showed these news articles for {symbol}:

{last_bot_message[chat_id]}

The user may want a summary, more details, or another stock.

IMPORTANT:
- The final message MUST be in the SAME LANGUAGE as the user.
- Ignore the languages of the articles.
- Ignore any other languages in the context.
"""

        closing_prompt = user_text.strip() or symbol
        closing = await generate_dynamic_prompt(
            closing_prompt,
            context=closing_context,
            chat_id=chat_id
        )
        await send_progressive(chat_id, closing)

    except Exception:
        traceback.print_exc()
        try:
            await send_progressive(chat_id, "Sorry — I hit an error while fetching news. Please try again later.")
        except Exception:
            pass
