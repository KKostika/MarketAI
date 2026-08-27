from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel


class StockHistoryBase(BaseModel):
    date: datetime
    open: float
    close: float
    high: float
    low: float
    volume: float | None = None


class StockHistoryRead(StockHistoryBase):
    id: int
    stock_id: int

    model_config = {
        "from_attributes": True
    }
