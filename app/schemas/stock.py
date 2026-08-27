from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel
from typing import List

from app.schemas.stock_history import StockHistoryBase


class StockBase(BaseModel):
    symbol: str


class StockHistoryRequest(BaseModel):
    symbol: str
    period: str  # "1m", "3m", "6m", "1y"


class StockHistoryResponse(BaseModel):
    symbol: str
    data: List[StockHistoryBase]

    model_config = {
        "from_attributes": True
    }
