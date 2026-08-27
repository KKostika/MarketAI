# app/api/users.py
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.core.database import get_session
from app.models.user import User
from app.schemas.user import UserCreate, UserRead
from app.core.security import get_password_hash

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/", response_model=UserRead)
def create_user(user: UserCreate, session: Session = Depends(get_session)) -> User:
    """
    It creates a new user account.

    Behavior implemented:
    - Validate the incoming payload.
    - Check for existing user by email and return 400 if already registered.
    - Hash the password and persist the new user.
    - Return the created user record.
    - Log and raise appropriate HTTP errors on failure.
    """
    if not user or not getattr(user, "email", None):
        raise HTTPException(status_code=400, detail="Invalid user payload")

    try:
        existing = session.exec(select(User).where(User.email == user.email)).first()
    except Exception:
        # DB read failed
        raise HTTPException(status_code=500, detail="Database error while checking existing user")

    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    try:
        new_user = User(
            email=user.email,
            username=user.username,
            hashed_password=get_password_hash(user.password)
        )
        session.add(new_user)
        session.commit()
        session.refresh(new_user)
    except Exception:
        # Ensure we don't leak internal errors to clients
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Failed to create user")

    return new_user


@router.get("/", response_model=List[UserRead])
def list_users(session: Session = Depends(get_session)) -> List[User]:
    """
    It returns a list of all registered users.

    Behavior implemented:
    - Query the database for users.
    - Return an empty list on failure or if no users exist.
    """
    try:
        users = session.exec(select(User)).all()
    except Exception:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Failed to fetch users")

    return users or []


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: int, session: Session = Depends(get_session)) -> User:
    """
    It returns a single user by ID.

    Behavior implemented:
    - Fetch the user by primary key.
    - Return 404 if not found.
    - Handle DB errors gracefully.
    """
    try:
        user = session.get(User, user_id)
    except Exception:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Database error while fetching user")

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user
