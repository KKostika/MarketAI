import json
import traceback
from typing import Any, Dict, Optional

from openai import OpenAI
from app.core.config import Settings

settings = Settings()
client = OpenAI(api_key=settings.OPENAI_API_KEY)


def run_agent(user_language: str, stock_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    It generates a structured financial analysis using GPT-4o-mini.

    Behavior implemented
    - Sends a system prompt that enforces language and exact JSON schema.
    - Calls the OpenAI chat completion and handles network or SDK errors.
    - Parses the model output robustly: accepts dict content, JSON string, or JSON embedded in text.
    - Validates and normalizes the result to the exact fields:
      sentiment (str), summary (str), risks (list[str]), opportunities (list[str]), scenarios (list[str]).
    - Returns an empty dict on failure to avoid unexpected fields propagating.
    """
    system_prompt = f"""
You are a multilingual financial assistant.

You analyze stock data and produce strictly structured financial insights.
You never invent numbers, never hallucinate fields, and never add commentary.

You must ALWAYS respond in the user's language.

Analyze the provided stock_data and generate a financial assessment containing:
- sentiment: short professional qualitative assessment
- summary: concise overview of the stock situation
- risks: list of risk factors
- opportunities: list of opportunity factors
- scenarios: list of possible forward-looking scenarios

Rules:
- Respond ONLY in the user's language: {user_language}.
- Use ONLY the provided stock_data.
- Do NOT invent numbers.
- Do NOT include explanations, disclaimers, or natural language outside JSON.
- Output MUST be valid JSON according to the schema.
- Keep the tone professional and concise.

Return only a json object with EXACTLY the following fileds:
{{
  "sentiment": string,
  "summary": string,
  "risks": [string],
  "opportunities": [string],
  "scenarios": [string]
}}
No additional fields. No surrounding text. No markdown.


"""

    user_prompt = f"""
Analyze the following stock data and produce the structured JSON exactly as specified:

{json.dumps(stock_data, ensure_ascii=False, indent=2)}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            max_tokens=800,
        )
    except Exception:
        # Network/SDK error or API key problem
        return {}

    # Extract content safely
    try:
        content = response.choices[0].message.content
    except Exception:
        try:
            content = json.dumps(response, default=str, ensure_ascii=False)
        except Exception:
            return {}

    # If content is already a dict-like object, validate and return it
    if isinstance(content, dict):
        parsed = content
    else:
        parsed = None
        if isinstance(content, str):
            text = content.strip()
            # Try direct JSON parse
            try:
                candidate = json.loads(text)
                if isinstance(candidate, dict):
                    parsed = candidate
            except Exception:
                # Try to extract JSON substring
                start = text.find("{")
                end = text.rfind("}")
                if start != -1 and end != -1 and end > start:
                    try:
                        candidate = json.loads(text[start:end + 1])
                        if isinstance(candidate, dict):
                            parsed = candidate
                    except Exception:
                        parsed = None

    if not isinstance(parsed, dict):
        return {}

    # Validate keys and normalize types
    allowed_keys = {"sentiment", "summary", "risks", "opportunities", "scenarios"}
    if not allowed_keys.issubset(set(parsed.keys())):
        return {}

    # Ensure list fields are lists of strings
    for key in ("risks", "opportunities", "scenarios"):
        val = parsed.get(key) or []
        if not isinstance(val, list):
            parsed[key] = [str(val)]
        else:
            parsed[key] = [str(x) for x in val]

    parsed["sentiment"] = str(parsed.get("sentiment", ""))
    parsed["summary"] = str(parsed.get("summary", ""))

    return parsed
