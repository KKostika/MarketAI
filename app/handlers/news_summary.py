import json
import asyncio
import traceback
from typing import Any, List, Optional

from sqlmodel import Session
from app.bot.sender import generate_dynamic_prompt, send_progressive
from app.db.engine import engine
from app.services.article_service import get_articles
from app.services.news_summary import summarize_news_articles

last_bot_message: dict[int, str] = {}

async def handle_news_summary(chat_id: int, symbol: str, user_text: str = "") -> None:
    """
    It generates and sends a premium summary of the latest news for a stock symbol.

    Behavior implemented:
    - Validate the symbol input.
    - Fetch articles from the service; if the service is blocking, run it in a thread executor.
    - Use the top three articles to produce a premium summary via the summarizer service.
    - Send the summary and a contextual closing prompt as progressive messages.
    - Save a short memory of the summarized articles for follow-up context.
    - Log full tracebacks and notify the user gracefully on error.
    """
    # Basic validation
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


        summary: Optional[str] = None
        try:
            if asyncio.iscoroutinefunction(summarize_news_articles):
                summary = await summarize_news_articles(top, user_text or symbol)
            else:
                loop = asyncio.get_running_loop()
                summary = await loop.run_in_executor(None, summarize_news_articles, top, (user_text or symbol))
        except Exception:
            traceback.print_exc()
            summary = None

        if summary:
            await send_progressive(
                chat_id,
                f"📰 *Preparing your summary... ({symbol})*\n\n{summary}"
            )
        else:
            await send_progressive(
                chat_id,
                f"📰 Could not generate a summary for *{symbol}* at the moment."
            )

        summarized_points: List[str] = []
        for a in top:
            if isinstance(a, dict):
                title = a.get("title", "") or ""
                source = a.get("source", "") or ""
            else:
                title = getattr(a, "title", "") or ""
                source = getattr(a, "source", "") or ""
            summarized_points.append(f"- {title} ({source})")

        last_bot_message[chat_id] = "\n".join(summarized_points)

        closing_context = f"""
The assistant just provided a summary of the latest news for {symbol}.

These were the summarized articles:
{last_bot_message[chat_id]}

The user responded: "{user_text or symbol}"

Generate a natural follow-up message in the SAME LANGUAGE as the user.
The follow-up should feel conversational and relevant to the summary context.
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
            await send_progressive(chat_id, "Sorry — I hit an error while generating the news summary. Please try again later.")
        except Exception:
            pass
