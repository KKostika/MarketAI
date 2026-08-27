from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session
from typing import Dict, Any, Optional
import json
import traceback

from app.core.database import get_session
from app.services.analysis_service import generate_full_analysis

router = APIRouter(prefix="/analysis", tags=["Analysis"])


@router.get("/full/{symbol}")
def full_analysis(
    symbol: str,
    user_language: str = Query("el", description="User language code, e.g. 'el' or 'en'"),
    session: Session = Depends(get_session)
) -> Dict[str, Any]:
    """
    It generates a full stock analysis for the requested symbol.

    Behavior implemented:
    - Validate inputs and normalize the symbol to uppercase.
    - Call generate_full_analysis(session, symbol, user_language).
    - Return a JSON object with the symbol and the analysis result.
    - Catch and log exceptions, returning a 500 HTTP error with a safe message.
    """
    if not symbol or not isinstance(symbol, str):
        raise HTTPException(status_code=400, detail="Invalid symbol")

    try:
        result = generate_full_analysis(
            session=session,
            symbol=symbol.upper(),
            user_language=user_language
        )
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Failed to generate analysis") from exc

    # Ensure result is JSON-serializable
    try:
        if isinstance(result, str):
            parsed = json.loads(result)
        elif isinstance(result, dict):
            parsed = result
        else:
            parsed = json.loads(json.dumps(result, default=str))
    except Exception:
        parsed = {"error": "Unexpected analysis format"}

    return {
        "symbol": symbol.upper(),
        "analysis": parsed
    }
