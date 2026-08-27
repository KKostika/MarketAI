from __future__ import annotations
from typing import List
from pydantic import BaseModel


class SentimentResult(BaseModel):
    """Overall sentiment distribution extracted from articles + price action."""
    positive: float
    negative: float
    neutral: float
    overall: str  # "positive", "negative", "neutral"


class ThematicPattern(BaseModel):
    """Detected thematic clusters (topics) with relative importance."""
    topic: str
    weight: float


class MarketScenario(BaseModel):
    """AI‑generated market scenario with confidence score."""
    summary: str
    confidence: float


class StockAnalysisResponse(BaseModel):
    """Final structured output returned by the AI agent."""
    symbol: str
    sentiment: SentimentResult
    themes: List[ThematicPattern]
    scenario: MarketScenario
    summary: str  

    model_config = {
        "from_attributes": True
    }

