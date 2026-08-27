import logging
from sqlmodel import SQLModel
from app.db.engine import engine

logger = logging.getLogger(__name__)

def create_db() -> None:
    """Create all database tables."""
    logger.info("Creating database tables...")
    SQLModel.metadata.create_all(engine)
    logger.info("Database initialization complete.")
