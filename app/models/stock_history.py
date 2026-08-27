from __future__ import annotations
from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional


class StockHistory(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    stock_id: int = Field(foreign_key="stock.id", index=True)
    date: datetime
    open: float
    close: float
    high: float
    low: float
    volume: Optional[float] = None
