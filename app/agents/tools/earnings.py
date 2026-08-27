import requests
from app.core.config import Settings

settings = Settings()
AV_KEY = settings.STOCK_API_KEY

BASE_URL = "https://www.alphavantage.co/query"


# ---------------------------------------------------------
# FETCH EARNINGS (REAL — ALPHA VANTAGE)
# ---------------------------------------------------------
async def fetch_earnings(symbol: str):
    params = {
        "function": "EARNINGS",
        "symbol": symbol,
        "apikey": AV_KEY
    }

    try:
        response = requests.get(BASE_URL, params=params)
        data = response.json()

        if "quarterlyEarnings" not in data:
            return None

        e = data["quarterlyEarnings"][0]

        return {
            "symbol": symbol,
            "date": e.get("reportedDate"),
            "eps_estimate": e.get("estimatedEPS"),
            "eps_actual": e.get("reportedEPS"),
            "surprise": e.get("surprise"),
            "surprise_pct": e.get("surprisePercentage"),
        }

    except Exception as e:
        print(f"[EARNINGS ERROR] {e}")
        return None
