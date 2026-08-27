import requests
from app.core.config import Settings

settings = Settings()
NEWS_API_KEY = settings.NEWS_API_KEY

BASE_URL = "https://newsapi.org/v2/everything"


# ---------------------------------------------------------
# FETCH NEWS FOR SYMBOL (REAL NewsAPI)
# ---------------------------------------------------------
async def fetch_news(symbol: str, limit: int = 5):
    params = {
        "q": symbol,
        "sortBy": "publishedAt",
        "language": "en",
        "pageSize": limit,
        "apiKey": NEWS_API_KEY,
    }

    try:
        response = requests.get(BASE_URL, params=params)
        data = response.json()

        if data.get("status") != "ok":
            return []

        articles = []
        for a in data.get("articles", []):
            articles.append({
                "title": a.get("title"),
                "summary": a.get("description") or "",
                "url": a.get("url"),
            })

        return articles

    except Exception as e:
        print(f"[NEWS ERROR] {e}")
        return []
