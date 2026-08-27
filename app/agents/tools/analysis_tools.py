from typing import List, Dict, Any

def tool_analyze_market_context(history: List[dict], articles: List[dict]) -> Dict[str, Any]:
    """
    This tool does not perform analysis itself.
    It simply returns the raw data (history + articles)
    back to the LLM so the agent can produce structured
    market analysis (sentiment, scenarios, risks, etc.)
    """
    return {
        "history": history,
        "articles": articles
    }
