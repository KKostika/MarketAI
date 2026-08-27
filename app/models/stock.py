from typing import Optional
from sqlmodel import SQLModel, Field

class Stock(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    symbol: str = Field(index=True, unique=True)
    name: Optional[str] = Field(default=None, nullable=True)
    exchange: Optional[str] = Field(default=None, nullable=True)
