"""
It detects polite closing messages from users.

Behavior implemented:
- Normalizes input (lowercase, strip, remove diacritics, collapse spaces, remove punctuation).
- Matches against a precomputed set of normalized close phrases in Greek and English.
- Uses both substring containment and whole-word checks to avoid false positives.
- Returns False for empty or invalid input.
"""
import re
import unicodedata
from typing import List

# ---------------------------------------------------------
# CLOSE MESSAGE PHRASES
# ---------------------------------------------------------
CLOSE_PHRASES: List[str] = [
    # English
    "no thank you",
    "no thanks",
    "no, thank you",
    "no, thanks",
    "i'm good",
    "im good",
    "that's all",
    "thats all",
    "thanks, that's all",
    "thanks thats all",

    # Greek (with and without accents)
    "όχι ευχαριστώ",
    "οχι ευχαριστω",
    "όχι, ευχαριστώ",
    "οχι, ευχαριστω",
    "δεν χρειάζομαι κάτι άλλο",
    "δεν χρειάζομαι τίποτα",
    "δεν χρειάζομαι τιποτα",
    "θα τα πούμε αύριο",
    "θα τα πουμε αυριο",
    "τέλος",
    "τελος",
    "ευχαριστώ",
    "ευχαριστω",
]

def _normalize_text(s: str) -> str:
    """
    Normalize text for robust matching:
    - lowercase, strip
    - remove diacritics (accents)
    - remove punctuation (keep letters/numbers/spaces)
    - collapse multiple spaces to single
    """
    if not isinstance(s, str):
        return ""
    s = s.lower().strip()
    # remove diacritics
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    # replace punctuation with space
    s = re.sub(r"[^\w\s]", " ", s)
    # collapse whitespace
    s = re.sub(r"\s+", " ", s).strip()
    return s

# Precompute normalized phrases for faster matching
_NORMALIZED_CLOSE_PHRASES = [_normalize_text(p) for p in CLOSE_PHRASES if p]

def is_close_message(text: str) -> bool:
    """
    Return True if the user's message is a polite closing phrase.

    Matching strategy:
    - Normalize both incoming text and known phrases.
    - Check for substring containment (covers multi-word phrases).
    - Also check whole-word matches for short single-token phrases.
    - Returns False for empty or non-string inputs.
    """
    try:
        if not text or not isinstance(text, str):
            return False

        t = _normalize_text(text)
        if not t:
            return False

        # Direct containment check (covers multi-word phrases)
        for phrase in _NORMALIZED_CLOSE_PHRASES:
            if phrase and phrase in t:
                return True

        # Fallback: check whole-word matches for single-token phrases
        tokens = set(t.split())
        for phrase in _NORMALIZED_CLOSE_PHRASES:
            if phrase and len(phrase.split()) == 1 and phrase in tokens:
                return True

        return False
    except Exception:
        # On unexpected errors, be conservative and return False
        return False
