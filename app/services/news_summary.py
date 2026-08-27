# app/agents/summarizer.py
from __future__ import annotations
import asyncio
import logging
from typing import List, Optional, Any

from app.agents.agent_loop import client

logger = logging.getLogger(__name__)


async def _call_llm(prompt: str, max_tokens: int = 150) -> Optional[str]:
    """
    Execute the LLM client call in a thread executor to avoid blocking the event loop.

    Returns the response text or None on error.
    """
    loop = asyncio.get_running_loop()

    def sync_call() -> Optional[str]:
        try:
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
            )
            return getattr(resp.choices[0].message, "content", None).strip()
        except Exception as exc:
            logger.exception("LLM sync call failed: %s", exc)
            return None

    return await loop.run_in_executor(None, sync_call)


async def summarize_news_articles(articles: List[Any], user_text: str) -> Optional[str]:
    """
    Produce a short premium summary (2–3 sentences) of the latest news articles for a stock.

    Rules:
    - Return 2–3 sentences in natural language.
    - Use the same language as the user when possible.
    - Do not invent events or facts.
    - Return None if there are no articles or on failure.

    Notes:
    - Limit input to the first 3 articles to keep the prompt concise.
    - The LLM call runs in an executor to avoid blocking the async event loop.
    """
    if not articles:
        return None

    base_points: List[str] = []
    for a in articles[:3]:
        try:
            title = getattr(a, "title", "") or ""
            desc = getattr(a, "content", "") or ""
            source = getattr(a, "source", "") or ""
            base_points.append(f"- {title} ({source}): {desc}")
        except Exception:
            logger.debug("Skipping malformed article object: %r", a, exc_info=True)
            continue

    if not base_points:
        return None

    base_text = "\n".join(base_points)

    prompt = f"""
The user wrote: "{user_text}"

Below is a list of real news headlines and descriptions:

{base_text}

Write a short, natural summary in the SAME LANGUAGE as the user.
Rules:
- 2–3 sentences maximum.
- Natural language.
- No emojis.
- No invented events.
- Capture the overall tone (positive, negative, mixed).
- Mention general themes (market pressure, demand, production, regulation).
"""

    try:
        summary = await _call_llm(prompt, max_tokens=150)
        if summary:
            return summary
        logger.warning("LLM returned empty summary for user_text=%r", user_text)
        return None
    except Exception as exc:
        logger.exception("summarize_news_articles failed: %s", exc)
        return None
