import re
import traceback
from typing import Any, Dict, Optional

from fastapi import APIRouter, Request
from sqlmodel import Session, text

from app.bot.quick_mode import quick_mode
from app.bot.close_detection import is_close_message
from app.bot.keyboards import send_action_keyboard, send_stock_keyboard
from app.bot.sender import generate_dynamic_prompt, send_message, send_progressive
from app.core.config import Settings
from app.db.engine import engine

from app.handlers.earnings import handle_earnings
from app.handlers.full_analysis import handle_full_analysis
from app.handlers.news_list import handle_news_list
from app.handlers.news_summary import handle_news_summary

from app.services.stock_service import get_stock_history_last_months, get_stock_price
from app.models.user import User
from app.utils.extract_symbol import extract_symbol
from app.utils.extract_months import extract_months


settings = Settings()
router = APIRouter(prefix="/telegram", tags=["Telegram"])

last_symbol_per_chat: Dict[int, Optional[str]] = {}
last_bot_message: Dict[int, str] = {}
last_user_message: Dict[int, str] = {}



@router.post("/webhook")
async def telegram_webhook(request: Request) -> Dict[str, Any]:
    """
    It receives Telegram webhook updates and routes them to the appropriate handlers.

    Behavior implemented:
    - Persist minimal user info to DB (if available) without failing the request on DB errors.
    - Handle callback_query actions (symbol selection, full analysis, news, summary, earnings, close).
    - Handle plain messages: symbol extraction, intent detection, and dispatch to handlers.
    - Protect the whole flow with try/except so the endpoint never returns 500 due to handler errors.
    - Maintain minimal per-chat state (last selected symbol, last bot message).
    """
    try:
        data = await request.json()
    except Exception:
        return {"status": "invalid_payload"}

    # -------------------------
    # Save user to DB
    # -------------------------
    try:
        if "message" in data:
            from_user = data["message"].get("from")
        elif "callback_query" in data:
            from_user = data["callback_query"].get("from")
        else:
            from_user = None

        if from_user:
            chat_id = from_user.get("id")
            if chat_id:
                try:
                    with Session(engine) as session:
                        user = session.query(User).filter(User.telegram_id == chat_id).first()
                        if not user:
                            user = User(
                                telegram_id=chat_id,
                                username=from_user.get("username"),
                                first_name=from_user.get("first_name"),
                                last_name=from_user.get("last_name")
                            )
                            session.add(user)
                            session.commit()
                except Exception:
                    # Don't fail the webhook if DB write fails log for debugging
                    traceback.print_exc()
    except Exception:
        traceback.print_exc()

    # -------------------------
    # CALLBACK QUERY
    # -------------------------
    try:
        if "callback_query" in data:
            cq = data["callback_query"]
            chat_id = cq.get("message", {}).get("chat", {}).get("id")
            cb = cq.get("data", "")
            user_text = last_user_message.get(chat_id, "")


            if user_text:
                last_user_message[chat_id] = user_text


            if not chat_id:
                return {"ok": True}

            # Select symbol
            if cb.startswith("symbol:"):
                symbol = cb.split(":", 1)[1]
                last_symbol_per_chat[chat_id] = symbol

                quick = quick_mode(symbol, user_text=symbol)
                if quick:
                    send_message(chat_id, quick)

                await send_action_keyboard(chat_id, symbol, user_text)
                return {"ok": True}

            # Full analysis
            if cb.startswith("full:"):
                symbol = cb.split(":", 1)[1]
                last_symbol_per_chat[chat_id] = symbol
                await handle_full_analysis(chat_id, symbol, user_text)
                return {"ok": True}

            # News list
            if cb.startswith("news:"):
                symbol = cb.split(":", 1)[1]
                last_symbol_per_chat[chat_id] = symbol
                await handle_news_list(chat_id, symbol, user_text)
                return {"ok": True}

            # Summary
            if cb.startswith("summary:"):
                symbol = cb.split(":", 1)[1]
                last_symbol_per_chat[chat_id] = symbol
                await handle_news_summary(chat_id, symbol, user_text)
                return {"ok": True}

            # Earnings
            if cb.startswith("earnings:"):
                symbol = cb.split(":", 1)[1]
                last_symbol_per_chat[chat_id] = symbol
                await handle_earnings(chat_id, symbol, user_text)
                return {"ok": True}

            # Close
            if cb == "close":
                msg = await generate_dynamic_prompt(
                    user_text,
                    context="closing conversation politely",
                    chat_id=chat_id
                )
                last_symbol_per_chat[chat_id] = None
                send_message(chat_id, msg)
                return {"ok": True}

            return {"ok": True}
    except Exception:
        traceback.print_exc()
        return {"ok": True}

    # -------------------------
    # PLAIN MESSAGE
    # -------------------------
    try:
        message = data.get("message", {}) or {}
        chat_id = message.get("chat", {}).get("id")
        text = message.get("text", "") or ""
        last_user_message[chat_id] = text
        


        if not chat_id:
            return {"status": "ignored"}

        # Close detection
        if is_close_message(text):
            msg = await generate_dynamic_prompt(
                text,
                context="closing the conversation politely and briefly",
                chat_id=chat_id
            )
            await send_progressive(chat_id, msg)
            return {"status": "closed"}


        # /start
        if text.strip() == "/start":
            msg = await generate_dynamic_prompt(
                text,
                context="welcome user and ask them to choose a stock",
                chat_id=chat_id
            )
            send_message(chat_id, msg)
            await send_stock_keyboard(chat_id, text)
            return {"status": "ok"}

        # Extract symbol
        symbol = extract_symbol(text)
        if symbol:
            last_symbol_per_chat[chat_id] = symbol
        else:
            symbol = last_symbol_per_chat.get(chat_id)


        if not symbol:
            msg = await generate_dynamic_prompt(
                text,
                context="ask user to choose a stock",
                chat_id=chat_id
            )
            send_message(chat_id, msg)
            await send_stock_keyboard(chat_id, text)
            return {"status": "waiting_for_symbol"}

        last_symbol_per_chat[chat_id] = symbol

        # Intent detection (defensive)
        text_lower = text.lower()
        intent = None

        if re.search(r"\b\d+\s*month", text_lower) or \
           re.search(r"\b\d+\s*μήν", text_lower) or \
           re.search(r"\b\d+m\b", text_lower):
            intent = "history_months"
        elif "news" in text_lower:
            intent = "news"
        elif "summary" in text_lower:
            intent = "summary"
        elif "earnings" in text_lower or "κέρδη" in text_lower:
            intent = "earnings"
        elif "price" in text_lower or "τιμή" in text_lower:
            intent = "price"
        elif "full analysis" in text_lower or "πλήρη ανάλυση" in text_lower or "πληρης αναλυση" in text_lower:
            intent = "full"
        else:
            intent = "quick"

        # Handle intents
        if intent == "full":
            await handle_full_analysis(chat_id, symbol, text)
            return {"status": "ok"}

        if intent == "news":
            await handle_news_list(chat_id, symbol, text)
            return {"status": "ok"}

        if intent == "summary":
            await handle_news_summary(chat_id, symbol, text)
            return {"status": "ok"}

        if intent == "earnings":
            await handle_earnings(chat_id, symbol, text)
            return {"status": "ok"}

        if intent == "price":
            try:
                price = get_stock_price(symbol)
                send_message(chat_id, f"{symbol} price: {price}")
            except Exception:
                traceback.print_exc()
                send_message(chat_id, "Could not fetch price at the moment.")
            return {"status": "ok"}

        if intent == "history_months":
            months = extract_months(text)
            if not months:
                months = 6

            try:
                with Session(engine) as session:
                    history = get_stock_history_last_months(session, symbol, months)
            except Exception:
                traceback.print_exc()
                history = []

            await send_progressive(
                chat_id,
                f"📈 Ιστορικό για {symbol} τους τελευταίους {months} μήνες φορτώθηκε!"
            )

            await handle_full_analysis(chat_id, symbol, text)
            return {"status": "ok"}

        # Default → quick mode
        if symbol:
            quick = quick_mode(symbol, user_text=text)
            if quick:
                send_message(chat_id, quick)

        await send_action_keyboard(chat_id, symbol, text)
        return {"status": "ok"}

    except Exception:
        traceback.print_exc()
        try:
            # Final fallback message to user, keep it short and friendly
            await send_progressive(chat_id, "Sorry — an unexpected error occurred. Please try again later.")
        except Exception:
            pass
        return {"status": "error"}




