from langdetect import detect

def detect_language(text: str) -> str:
    """
    Detect user language using langdetect.
    Returns ISO language code (e.g., 'en', 'el', 'ru', 'de', 'it', 'es').
    """
    if not text:
        return "en"
    try:
        return detect(text)
    except:
        return "en"
