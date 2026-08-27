from __future__ import annotations
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field

class Article(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    stock_symbol: str = Field(foreign_key="stock.symbol")
    title: str
    url: str
    source: Optional[str] = None
    published_at: datetime
    content: Optional[str] = None

