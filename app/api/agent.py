from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any, Optional
import json

from app.core.database import get_session
from app.agents.agent_loop import run_agent  
from sqlmodel import Session
router = APIRouter(prefix="/agent", tags=["Agent"])


@router.get("/analyze/{symbol}")
def analyze(
    symbol: str,
    session: Session = Depends(get_session),
    user_language: Optional[str] = Query("en", description="User language code, e.g. 'en' or 'el'")
) -> Dict[str, Any]:
    """
    Agent-based stock analysis using the run_agent helper.

    Behavior implemented:
    - Validate inputs.
    - Call run_agent(user_language, stock_data) with a minimal stock_data payload.
    - Return the parsed dict result or an empty dict on failure.
    - Log and raise a 500 HTTP error if something unexpected happens.
    """
    if not symbol or not isinstance(symbol, str):
        raise HTTPException(status_code=400, detail="Invalid symbol")

    stock_data = {"symbol": symbol}

    try:
        result = run_agent(user_language, stock_data)
    except Exception as exc:
        # If the agent runner raises, log and return a 500 with a safe message
        raise HTTPException(status_code=500, detail="Agent execution failed") from exc

    # Ensure we return a JSON-serializable dict
    if not isinstance(result, dict):
        return {}

    return result
