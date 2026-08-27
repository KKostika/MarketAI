import re
from typing import Optional

"""
Symbol extraction module.

This function is responsible ONLY for detecting actual stock symbols
from user text. It intentionally ignores intent-related keywords such as
FULL, NEWS, SUMMARY, EARNINGS, PRICE, CLOSE, ANALYSIS, because these
words are NOT stock tickers and previously caused false positives.

The Webhook performs intent detection separately, so this module must
focus strictly on identifying valid stock symbols (TSLA, AAPL, MSFT, NVDA, AMZN)
or company names (Tesla → TSLA, Apple → AAPL, etc.).
"""

# Words that must NOT be treated as symbols
COMMAND_WORDS = {
    "FULL", "NEWS", "SUMMARY", "EARNINGS", "PRICE", "CLOSE", "ANALYSIS"
}

# Mapping company names → stock symbols
NAME_TO_SYMBOL = {
    "TESLA": "TSLA",
    "APPLE": "AAPL",
    "MICROSOFT": "MSFT",
    "NVIDIA": "NVDA",
    "AMAZON": "AMZN",
}

# Valid stock tickers
VALID_SYMBOLS = {"TSLA", "AAPL", "MSFT", "NVDA", "AMZN"}


def extract_symbol(text: str) -> Optional[str]:
    """
    Extract a stock symbol from natural-language text.

    Returns
    -------
    Optional[str]
        A valid stock ticker (e.g., "AAPL") or None if not found.

    Behavior
    --------
    - Detects known tickers directly (TSLA, AAPL, MSFT, NVDA, AMZN).
    - Detects company names and maps them to tickers.
    - Uses regex to detect uppercase tokens 2–5 letters long.
    - Ignores intent-related keywords (FULL, NEWS, SUMMARY, etc.).
    """
    if not text:
        return None

    upper = text.upper()

    # Direct match for valid symbols
    for sym in VALID_SYMBOLS:
        if sym in upper:
            return sym

    # Company name → symbol
    for name, sym in NAME_TO_SYMBOL.items():
        if name in upper:
            return sym

    # Regex uppercase tokens 2–5 chars
    matches = re.findall(r"\b[A-Z]{2,5}\b", upper)
    for m in matches:
        if m in VALID_SYMBOLS:
            return m
        if m in COMMAND_WORDS:
            continue  # ignore intent keywords

    return None
