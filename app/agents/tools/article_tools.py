from sqlmodel import Session
from app.services.article_service import get_articles

def tool_get_articles(session: Session, symbol: str):
    articles = get_articles(session, symbol)

    serialized = []
    for a in articles:
        item = a.dict()
        # ALWAYS convert published_at to string (no isinstance, no datetime)
        item["published_at"] = str(item["published_at"])
        serialized.append(item)

    return serialized


