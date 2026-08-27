"""
It generates and sends Telegram inline keyboards for stock selection and actions.

Behavior implemented:
- Uses the configured TELEGRAM_BOT_TOKEN from Settings without exposing it.
- Runs blocking HTTP calls in a thread to avoid blocking the event loop.
- Defensive input validation and graceful error handling.
- Reply markup is JSON-encoded consistently.
"""
import json
import traceback
from typing import Any, Dict

import requests
from anyio.to_thread import run_sync

from app.core.config import Settings

settings = Settings()
BASE_URL = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}"


async def _post(url: str, payload: Dict[str, Any]) -> None:
    """
    Helper that posts JSON to Telegram using requests in a thread.
    """
    def _send() -> None:
        try:
            requests.post(url, json=payload, timeout=10)
        except Exception:
            traceback.print_exc()

    await run_sync(_send)


async def send_stock_keyboard(chat_id: int, user_text: str = "") -> None:
    """
    It generates and sends a static stock selection keyboard.

    - Sends a short prompt and an inline keyboard with common tickers.
    - Uses Markdown parse mode where appropriate.
    """
    if not chat_id:
        return

    msg = "Please select a stock:"
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "TSLA", "callback_data": "symbol:TSLA"},
                {"text": "NVDA", "callback_data": "symbol:NVDA"},
            ],
            [
                {"text": "AAPL", "callback_data": "symbol:AAPL"},
                {"text": "MSFT", "callback_data": "symbol:MSFT"},
            ],
            [
                {"text": "AMZN", "callback_data": "symbol:AMZN"},
            ]
        ]
    }

    payload = {
        "chat_id": chat_id,
        "text": msg,
        "parse_mode": "Markdown",
        "reply_markup": json.dumps(keyboard),
    }

    await _post(f"{BASE_URL}/sendMessage", payload)


async def send_action_keyboard(chat_id: int, symbol: str, user_text: str = "") -> None:
    """
    It generates and sends an action keyboard for a selected stock.

    - Provides actions: News, Earnings, Full Analysis, Close.
    - Ensures symbol is present before sending.
    """
    if not chat_id or not symbol:
        return

    msg = f"What would you like to see for the stock {symbol}?"
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "📰 News", "callback_data": f"news:{symbol}"},
                {"text": "💰 Earnings", "callback_data": f"earnings:{symbol}"},
            ],
            [
                {"text": "📊 Full Analysis", "callback_data": f"full:{symbol}"},
            ],
            [
                {"text": "❌ Close", "callback_data": "close"},
            ]
        ]
    }

    payload = {
        "chat_id": chat_id,
        "text": msg,
        "parse_mode": "Markdown",
        "reply_markup": json.dumps(keyboard),
    }

    await _post(f"{BASE_URL}/sendMessage", payload)


# async def send_start_keyboard(chat_id: int) -> None:
#     """
#     It generates and sends the initial start keyboard when the user starts the bot.

#     - Buttons are intentionally simple and in English for consistent UX.
#     """
#     if not chat_id:
#         return

#     keyboard = {
#         "inline_keyboard": [
#             [
#                 {"text": "TSLA", "callback_data": "symbol:TSLA"},
#                 {"text": "AAPL", "callback_data": "symbol:AAPL"},
#             ],
#             [
#                 {"text": "NVDA", "callback_data": "symbol:NVDA"},
#                 {"text": "MSFT", "callback_data": "symbol:MSFT"},
#             ],
#             [
#                 {"text": "AMZN", "callback_data": "symbol:AMZN"},
#             ]
#         ]
#     }

#     payload = {
#         "chat_id": chat_id,
#         "text": "Choose a stock:",
#         "parse_mode": "Markdown",
#         "reply_markup": json.dumps(keyboard),
#     }

#     await _post(f"{BASE_URL}/sendMessage", payload)


# async def send_symbol_keyboard(chat_id: int, symbol: str) -> None:
#     """
#     It generates and sends a compact inline keyboard for a specific symbol.

#     - Offers Full Analysis, Latest News, Earnings and Close options.
#     """
#     if not chat_id or not symbol:
#         return

#     keyboard = {
#         "inline_keyboard": [
#             [
#                 {"text": "Full Analysis 📊", "callback_data": f"full:{symbol}"},
#                 {"text": "Latest News 📰", "callback_data": f"news:{symbol}"}
#             ],
#             [
#                 {"text": "Earnings 💰", "callback_data": f"earnings:{symbol}"},
#                 {"text": "Close ❌", "callback_data": "close"}
#             ]
#         ]
#     }

#     payload = {
#         "chat_id": chat_id,
#         "text": f"Choose an option for *{symbol}*:",
#         "parse_mode": "Markdown",
#         "reply_markup": json.dumps(keyboard),
#     }

#     await _post(f"{BASE_URL}/sendMessage", payload)
