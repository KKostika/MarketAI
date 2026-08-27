from __future__ import annotations
import logging
from sqlmodel import Session
from openai import OpenAI

from app.services.stock_service import get_stock_history
from app.services.article_service import get_articles

from app.schemas.stock import StockHistoryRequest
from app.schemas.agent_analysis import (
    StockAnalysisResponse,
    SentimentResult,
    ThematicPattern,
    MarketScenario
)
from app.core.config import Settings


logger = logging.getLogger(__name__)


# ---------------------------------------------------------
# Singleton OpenAI client
# ---------------------------------------------------------
_settings = Settings()
if not _settings.OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is missing. Check your .env file.")

client = OpenAI(api_key=_settings.OPENAI_API_KEY)


# ---------------------------------------------------------
# Prompt template
# ---------------------------------------------------------
AI_PROMPT = """
You are a financial analysis agent.

You receive:
1. Stock price history (list of OHLCV points)
2. Trend analysis (trend, percent change, volatility, description)
3. News articles (title, source, published_at)

Your task:
- Interpret the trend analysis
- Compute overall sentiment
- Extract thematic patterns
- Generate a market scenario
- Produce a final summary

Return ONLY JSON with this structure:

{
  "trend": {
    "trend": str,
    "change_percent": float,
    "volatility_percent": float,
    "description": str
  },
  "sentiment": {
    "positive": float,
    "negative": float,
    "neutral": float,
    "overall": "positive" | "negative" | "neutral"
  },
  "themes": [
    {"topic": str, "weight": float}
  ],
  "scenario": {
    "summary": str,
    "confidence": float
  },
  "summary": str
}
"""


def analyze_trend(history):
    if not history or len(history) < 5:
        return {
            "trend": "insufficient_data",
            "trend_change_percent": 0,
            "volatility_percent": 0,
            "description": "Not enough data for trend analysis."
        }

    closes = [h.close for h in history]

    first = closes[0]
    last = closes[-1]

    change = ((last - first) / first) * 100

    diffs = []
    for i in range(1, len(closes)):
        diffs.append(abs(closes[i] - closes[i-1]))

    avg_diff = sum(diffs) / len(diffs)
    volatility = avg_diff / last * 100

    if change > 10:
        trend = "uptrend"
        desc = f"Uptrend (+{change:.2f}%)."
    elif change < -10:
        trend = "downtrend"
        desc = f"Downtrend ({change:.2f}%)."
    else:
        trend = "sideways"
        desc = f"Sideways ({change:.2f}%)."

    if volatility > 5:
        vol_desc = f"High volatility ({volatility:.2f}%)."
    else:
        vol_desc = f"Low volatility ({volatility:.2f}%)."

    return {
        "trend": trend,
        "trend_change_percent": round(change, 2),
        "volatility_percent": round(volatility, 2),
        "description": f"{desc} {vol_desc}"
    }

# ---------------------------------------------------------
# Run OpenAI with structured output
# ---------------------------------------------------------
def run_ai_analysis(stock_data, trend_info, articles):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "You are a financial analysis agent."},
                {"role": "user", "content": AI_PROMPT},
                {"role": "user", "content": f"Stock history: {stock_data}"},
                {"role": "user", "content": f"Trend analysis: {trend_info}"},
                {"role": "user", "content": f"Articles: {articles}"}
            ]
        )

        return response.choices[0].message.parsed

    except Exception as e:
        logger.error(f"AI analysis failed: {e}")
        raise RuntimeError("AI analysis failed") from e



# ---------------------------------------------------------
# Main AI analysis function
# ---------------------------------------------------------
def analyze_stock(session: Session, symbol: str, period: str = "3m") -> StockAnalysisResponse:
    stock_request = StockHistoryRequest(symbol=symbol, period=period)
    stock_history = get_stock_history(session, stock_request)

    articles = get_articles(session, symbol)

    trend_info = analyze_trend(stock_history)

    ai_output = run_ai_analysis(
        stock_data=[p.dict() for p in stock_history],
        trend_info=trend_info,
        articles=[a.dict() for a in articles]
    )

    return StockAnalysisResponse(
        symbol=symbol,
        trend=trend_info,
        sentiment=SentimentResult(**ai_output["sentiment"]),
        themes=[ThematicPattern(**t) for t in ai_output["themes"]],
        scenario=MarketScenario(**ai_output["scenario"]),
        summary=ai_output["summary"]
    )



