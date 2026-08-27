import asyncio
import traceback
from typing import Optional, Any

from app.bot.sender import send_progressive
from app.services.stock_service import get_earnings

async def handle_earnings(chat_id: int, symbol: str, user_text: Optional[str] = None) -> None:
    """
    It generates and sends the latest earnings reports for a given stock symbol.

    Behavior implemented:
    - Validate the symbol input.
    - Fetch earnings from the service; if the service is blocking, run it in a thread executor.
    - Normalize and defensively format the results.
    - Send up to the top 3 most recent earnings using progressive messages.
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
        # Fetch earnings: support both async and sync implementations
        if asyncio.iscoroutinefunction(get_earnings):
            earnings = await get_earnings(symbol)
        else:
            loop = asyncio.get_running_loop()
            earnings = await loop.run_in_executor(None, get_earnings, symbol)

        # Defensive normalization
        if not earnings:
            await send_progressive(chat_id, f"No earnings found for *{symbol}* 💰")
            return

        if not isinstance(earnings, (list, tuple)):
            # If service returned a dict with a list under a key, try common keys
            if isinstance(earnings, dict):
                for key in ("quarterlyEarnings", "earnings", "data", "results"):
                    if key in earnings and isinstance(earnings[key], (list, tuple)):
                        earnings = earnings[key]
                        break
            # If still not list-like, wrap single item
            if not isinstance(earnings, (list, tuple)):
                earnings = [earnings]

        await send_progressive(chat_id, f"💰 *Earnings for {symbol}:*")

        # Send up to top 3
        top = earnings[:3]
        for e in top:
            # Support multiple possible field names returned by different APIs
            fiscal = e.get("fiscalDateEnding") or e.get("reportedDate") or "N/A"
            eps = e.get("reportedEPS") or e.get("eps") or e.get("estimatedEPS") or "N/A"
            surprise = e.get("surprisePercentage") or e.get("surprise") or "N/A"

            # Ensure types are strings for safe formatting
            fiscal = str(fiscal)
            eps = str(eps)
            surprise = str(surprise).rstrip("%")

            msg = (
                f"- *{fiscal}*\n"
                f"  EPS: {eps}\n"
                f"  Surprise: {surprise}%\n"
            )
            await send_progressive(chat_id, msg)

        await send_progressive(chat_id, "Want to see something else? 😊")

    except Exception:
        # Full traceback for debugging; graceful user message
        traceback.print_exc()
        try:
            await send_progressive(chat_id, "Sorry — I hit an error while fetching earnings. Please try again later.")
        except Exception:
            pass
