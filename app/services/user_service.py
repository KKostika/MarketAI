# app/services/user_service.py
from __future__ import annotations
import logging
from typing import Optional

from sqlmodel import Session, select

from app.models.user import User
from app.schemas.user import UserCreate
from app.core.security import verify_password, get_password_hash

logger = logging.getLogger(__name__)


def get_user_by_email(session: Session, email: str) -> Optional[User]:
    """
    Retrieve a user by email.

    Returns the User instance or None if not found or on error.
    """
    statement = select(User).where(User.email == email)
    try:
        return session.exec(statement).first()
    except Exception:
        logger.exception("Failed to query user by email=%s", email)
        return None


def get_user_by_username(session: Session, username: str) -> Optional[User]:
    """
    Retrieve a user by username.

    Returns the User instance or None if not found or on error.
    """
    statement = select(User).where(User.username == username)
    try:
        return session.exec(statement).first()
    except Exception:
        logger.exception("Failed to query user by username=%s", username)
        return None


def create_user(session: Session, user_data: UserCreate) -> User:
    """
    Create a new user with hashed password.

    Validates uniqueness of email and username, hashes the password,
    persists the user, and returns the created User instance.

    Raises ValueError for validation failures and re-raises DB exceptions.
    """
    # Validate duplicates
    existing = get_user_by_email(session, user_data.email)
    if existing:
        raise ValueError("Email already registered")

    existing = get_user_by_username(session, user_data.username)
    if existing:
        raise ValueError("Username already taken")

    hashed_password = get_password_hash(user_data.password)

    user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=hashed_password
    )

    session.add(user)
    try:
        session.commit()
        session.refresh(user)
        logger.info("Created user id=%s email=%s", user.id, user.email)
        return user
    except Exception:
        session.rollback()
        logger.exception("Failed to create user email=%s username=%s", user_data.email, user_data.username)
        raise


def authenticate_user(session: Session, email: str, password: str) -> Optional[User]:
    """
    Authenticate a user by email and password.

    Returns the User instance on success, or None on failure.
    """
    try:
        user = get_user_by_email(session, email)
    except Exception:
        logger.exception("Error while retrieving user for authentication email=%s", email)
        return None

    if not user:
        logger.debug("Authentication failed: user not found email=%s", email)
        return None

    try:
        if not verify_password(password, user.hashed_password):
            logger.debug("Authentication failed: invalid password for email=%s", email)
            return None
    except Exception:
        logger.exception("Password verification error for email=%s", email)
        return None

    return user
