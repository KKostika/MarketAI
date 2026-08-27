from __future__ import annotations
from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    # Telegram fields
    telegram_id: int = Field(index=True, unique=True)
    telegram_username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None

   
    email: Optional[str] = Field(default=None, index=True, unique=True)
    username: Optional[str] = Field(default=None, index=True, unique=True)
    hashed_password: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)

