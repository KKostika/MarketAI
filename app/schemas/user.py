from __future__ import annotations
from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    """Shared fields for user objects."""
    email: EmailStr
    username: str


class UserCreate(UserBase):
    """Schema for user registration."""
    password: str


class UserLogin(BaseModel):
    """Schema for login requests."""
    email: EmailStr
    password: str


class UserRead(UserBase):
    """Schema returned when reading user data."""
    id: int

    model_config = {
        "from_attributes": True
    }
