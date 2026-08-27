from __future__ import annotations
import logging
from typing import Optional, Iterable, Tuple

logger = logging.getLogger(__name__)

# Intent keyword sets
_INTENT_KEYWORDS = {
    "full": {"full", "analysis", "detailed", "λεπτομερή", "λεπτομερη", "πλήρη", "πληρη"},
    "news": {"news", "latest", "articles", "άρθρα", "αρθρα", "άρθρο", "αρθρο", "νέα", "νεα"},
    "earnings": {"earnings", "eps", "κέρδη", "κερδη"},
    "price": {"price", "current", "τιμή", "τιμη", "τρέχουσα", "τρεχουσα", "τρεχουσα τιμή", "τρέχουσα τιμή"},
    "summary": {"summary", "summaries", "σύνοψη", "περίληψη", "περιληψη", "συνοψη", "συνοπτική", "συνοπτικη"},
    "quick": {"quick", "brief", "γρήγορη", "γρηγορη", "σύντομη", "συντομη"},
}


def extract_intent_and_symbol(text: str, known_symbols: Iterable[str] | None = None) -> Tuple[str, Optional[str]]:
    """
    Extract ONLY the user's intent from free text.

    Parameters
    ----------
    text : str
        The user's natural-language message.
    known_symbols : Iterable[str] | None
        Ignored in this implementation. Symbol extraction is handled
        by the Webhook layer.

    Returns
    -------
    (intent, symbol)
        intent : str
            One of: "full", "news", "earnings", "price", "summary", "quick".
        symbol : None
            Always None. Symbol extraction is intentionally disabled here.

    Notes
    -----
    - Intent priority order:
        full > news > earnings > price > summary > quick
    - Symbol extraction MUST be done in the Webhook using extract_symbol().
    - This function is used by LLM prompt builders (quick_mode, full analysis, etc.)
      and must NOT interfere with symbol routing.
    """
    if not text or not isinstance(text, str):
        return "quick", None

    try:
        lower_text = text.lower()
        intent = _detect_intent(lower_text)
        return intent, None

    except Exception:
        logger.exception("extract_intent_and_symbol failed for text=%r", text)
        return "quick", None


def _detect_intent(lower_text: str) -> str:
    """
    Determine intent from normalized lowercase text using keyword sets.

    Priority order:
        full → news → earnings → price → summary → quick
    """
    for intent in ("full", "news", "earnings", "price", "summary"):
        keywords = _INTENT_KEYWORDS.get(intent, set())
        if any(k in lower_text for k in keywords):
            return intent
    return "quick"