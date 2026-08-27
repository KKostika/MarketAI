from sqlmodel import Session
from app.schemas.stock import StockHistoryRequest
from app.services.stock_service import get_stock_history

def tool_get_stock_history(session: Session, symbol: str, period: str = "3m"):
    request = StockHistoryRequest(symbol=symbol, period=period)
    history = get_stock_history(session, request)

    serialized = []
    for h in history:
        item = h.dict()
        item["date"] = str(item["date"])
        serialized.append(item)

    return serialized
