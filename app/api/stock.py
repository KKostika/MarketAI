from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from typing import Any, Dict

from app.core.database import get_session
from app.services.stock_service import get_stock_history
from app.schemas.stock import StockHistoryRequest, StockHistoryResponse

router = APIRouter(prefix="/stocks", tags=["Stocks"])


@router.post("/history", response_model=StockHistoryResponse)
def stock_history(request: StockHistoryRequest, session: Session = Depends(get_session)) -> StockHistoryResponse:
    """
    It generates historical OHLCV data for a given stock symbol and period.

    Behavior implemented:
    - Validate the incoming request payload.
    - Call get_stock_history(session, request) to retrieve OHLCV data.
    - Normalize the returned data to a JSON-serializable structure.
    - Return a StockHistoryResponse or raise an HTTP error on failure.
    """
    # Basic validation
    if not request or not getattr(request, "symbol", None):
        raise HTTPException(status_code=400, detail="Invalid request: missing symbol")

    try:
        data = get_stock_history(session, request)
    except Exception as exc:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Failed to fetch stock history") from exc

    # Defensive normalization: ensure data is serializable
    try:
        if data is None:
            normalized = []
        elif isinstance(data, (list, tuple)):
            normalized = list(data)
        else:
            # Try to coerce single-item responses into a list
            normalized = [data]
    except Exception:
        normalized = []

    return StockHistoryResponse(symbol=request.symbol, data=normalized)
