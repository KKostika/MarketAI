"""
It generates a short, natural quick stock update in the same language as the user.

Behavior implemented:
- Validates inputs and handles missing symbol/user_text.
- Retrieves current price and recent history via service functions.
- Builds a concise base sentence describing price and movement.
- Optionally asks the LLM to rewrite the sentence in the user's language.
- Handles network/SDK errors and returns None on failure.
"""
import traceback
from typing import Optional, Dict, Any

from app.core.config import Settings
from app.services.stock_service import get_stock_price, fetch_stock_history_from_api


try:
    from openai import OpenAI
    settings = Settings()
    _client = OpenAI(api_key=settings.OPENAI_API_KEY)
except Exception:
    _client = None


def _determine_movement(history: list[Dict[str, Any]]) -> str:
    if not history or len(history) < 2:
        return "stable"
    try:
        last = float(history[-1].get("close", history[-1].get("Close", 0)))
        prev = float(history[-2].get("close", history[-2].get("Close", 0)))
        if last > prev:
            return "up"
        if last < prev:
            return "down"
        return "flat"
    except Exception:
        return "stable"


def quick_mode(symbol: str, user_text: str) -> Optional[str]:
    """
    It generates a quick stock update sentence.

    Returns a single natural sentence in the user's language (if LLM available),
    or a fallback English sentence. Returns None if symbol or price is unavailable.
    """
    if not symbol or not isinstance(symbol, str):
        return None

    # Current price
    try:
        price = get_stock_price(symbol)
    except Exception:
        traceback.print_exc()
        price = None

    if price is None:
        return None

    # Movement (last 2 days) using API history
    try:
        history = fetch_stock_history_from_api(symbol, period="1mo") or []
    except Exception:
        traceback.print_exc()
        history = []

    movement = _determine_movement(history)

    movement_map = {
        "up": "has shown a mild upward trend recently",
        "down": "has seen slight downward pressure lately",
        "flat": "is trading flat with limited volatility",
        "stable": "is stable with no major price shifts"
    }
    movement_text = movement_map.get(movement, movement_map["stable"])

    base_sentence = f"{symbol} is currently trading at ${float(price):.2f} and {movement_text}."


    if _client is None:
        return base_sentence

    # Ask LLM to rewrite in user's language (best-effort)
    prompt = f"""
Rewrite the following single sentence in the SAME LANGUAGE as the user, adding a short, natural micro-context
(e.g., recent trend or mild market influence) but WITHOUT inventing specific news events.

User wrote: "{user_text}"

Sentence:
"{base_sentence}"

Rules:
- One sentence only.
- Natural language.
- No emojis.
- No bullet points.
- Do not invent facts or numbers.
"""

    try:
        response = _client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=80,
        )
        
        content = None
        try:
            content = response.choices[0].message.content
        except Exception:
            try:
                content = str(response)
            except Exception:
                content = None

        if isinstance(content, str) and content.strip():
            return content.strip()
        return base_sentence
    except Exception:
        traceback.print_exc()
        return base_sentence
