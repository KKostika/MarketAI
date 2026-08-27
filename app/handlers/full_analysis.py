import json
import asyncio
import traceback
from typing import Any, Dict, Optional

from sqlmodel import Session
from app.bot.sender import generate_dynamic_prompt, send_progressive
from app.db.engine import engine 
from app.services.analysis_service import generate_full_analysis
from app.utils.extract_lang import detect_language


async def handle_full_analysis(chat_id: int, symbol: str, user_text: str = "") -> None:
    """
    Generates a full stock analysis and sends it to the user in multiple progressive messages.

    Behavior I implemented:
    - Validate inputs (symbol must be a non-empty string).
    - Produce a short dynamic intro using the LLM prompt helper.
    - Fetch the analysis from the service. If the service is blocking, run it in a thread executor
      and provide a DB session; if it's async, await it directly.
    - Normalize the service output to a dict (JSON string -> dict fallback).
    - Send sections in separate progressive messages: sentiment, summary, risks,
      opportunities, scenarios, and a dynamic closing.
    - Catch and log any exception and notify the user gracefully without raising 500s.
    """
    # Basic input validation
    if not symbol or not isinstance(symbol, str):
        try:
            await send_progressive(chat_id, "Invalid symbol provided.")
        except Exception:
            pass
        return

    try:
        intro_prompt = user_text.strip() or symbol
        intro = await generate_dynamic_prompt(
            intro_prompt,
            context="introduce a full stock analysis in a friendly, natural way",
            chat_id=chat_id
        )
        await send_progressive(chat_id, intro)

        # Fetch analysis (handle sync vs async service)
        if asyncio.iscoroutinefunction(generate_full_analysis):
            analysis = await generate_full_analysis(
                session=None,
                symbol=symbol,
                user_language=detect_language(user_text)
            )
        else:
            def _call_with_session() -> Any:
                with Session(engine) as session:
                    return generate_full_analysis(
                        session=session,
                        symbol=symbol,
                        user_language=detect_language(user_text)
                    )
            loop = asyncio.get_running_loop()
            analysis = await loop.run_in_executor(None, _call_with_session)

        # Normalize analysis to dict
        if isinstance(analysis, str):
            try:
                analysis = json.loads(analysis)
            except Exception:
                analysis = {
                    "summary": str(analysis),
                    "sentiment": "N/A",
                    "risks": [],
                    "opportunities": [],
                    "scenarios": []
                }

        if not isinstance(analysis, dict):
            analysis = {
                "summary": str(analysis),
                "sentiment": "N/A",
                "risks": [],
                "opportunities": [],
                "scenarios": []
            }

        # Ensure keys exist and are of expected types
        sentiment = analysis.get("sentiment", "N/A")
        summary = analysis.get("summary", "No summary available.")
        risks = analysis.get("risks") or []
        opportunities = analysis.get("opportunities") or []
        scenarios = analysis.get("scenarios") or []

        # Send sections progressively with defensive formatting
        await send_progressive(chat_id, f"🧠 *Sentiment for {symbol}*\n{sentiment}")
        await send_progressive(chat_id, f"📌 *Summary*\n{summary}")

        risks_text = "\n".join([f"• {r}" for r in risks]) if risks else "No major risks identified."
        await send_progressive(chat_id, f"⚠️ *Risks*\n{risks_text}")

        opp_text = "\n".join([f"• {o}" for o in opportunities]) if opportunities else "No immediate opportunities identified."
        await send_progressive(chat_id, f"💡 *Opportunities*\n{opp_text}")

        scen_text = "\n".join([f"• {s}" for s in scenarios]) if scenarios else "No scenarios available."
        await send_progressive(chat_id, f"📊 *Possible Scenarios*\n{scen_text}")


        closing_prompt = user_text.strip() or symbol
        closing = await generate_dynamic_prompt(
            closing_prompt,
            context="closing message after a full stock analysis",
            chat_id=chat_id
        )
        await send_progressive(chat_id, closing)

    except Exception:
        traceback.print_exc()
        try:
            await send_progressive(chat_id, "Sorry — I hit an error while generating the analysis. Please try again later.")
        except Exception:
            pass
