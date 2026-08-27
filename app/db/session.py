from sqlmodel import Session
from app.db.engine import engine

def get_session():
    """Dependency that provides a SQLModel session."""
    with Session(engine) as session:
        yield session
