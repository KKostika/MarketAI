import re
from typing import Optional

"""
Extract the number of months from natural-language text.

Supported formats:
- Greek: "6 μηνες", "6 μην", "6 μήνες"
- English: "6 month", "6 months"
- Shorthand: "6m"

Returns
-------
int | None
    The number of months if detected, otherwise None.
"""

def extract_months(text: str) -> Optional[int]:
    if not text:
        return None

    # Greek: "6 μηνες", "6 μην", "6 μήνες"
    match = re.search(r"(\d+)\s*μήν", text, flags=re.IGNORECASE)
    if match:
        return int(match.group(1))

    # English: "6 month", "6 months"
    match = re.search(r"(\d+)\s*month", text, flags=re.IGNORECASE)
    if match:
        return int(match.group(1))

    # Shorthand: "6m"
    match = re.search(r"(\d+)m\b", text, flags=re.IGNORECASE)
    if match:
        return int(match.group(1))

    return None
