"""
LLM-powered extraction using Claude Haiku as fallback when fast extraction confidence < 0.8.
Truncates HTML intelligently to ~8000 tokens before sending to the model.
"""

from __future__ import annotations

import os
import re

import orjson

_MAX_CHARS = 32000  # ~8000 tokens @ 4 chars/token
_HEAD_CHARS = 10000
_TAIL_CHARS = 5000
_KEYWORD_CONTEXT_CHARS = 500  # chars around each keyword match


def _truncate_html(html: str, schema: dict) -> str:
    """
    Smart truncation: keep first 10k + last 5k chars + sections near schema keywords.
    """
    if len(html) <= _MAX_CHARS:
        return html

    # Collect keywords from schema field names
    keywords = list(schema.get("properties", {}).keys())

    head = html[:_HEAD_CHARS]
    tail = html[-_TAIL_CHARS:]

    # Find sections containing schema keywords (case-insensitive)
    keyword_sections: list[str] = []
    if keywords:
        for keyword in keywords:
            pattern = re.compile(re.escape(keyword), re.IGNORECASE)
            for match in pattern.finditer(html):
                start = max(0, match.start() - _KEYWORD_CONTEXT_CHARS // 2)
                end = min(len(html), match.end() + _KEYWORD_CONTEXT_CHARS // 2)
                section = html[start:end]
                if section not in keyword_sections:
                    keyword_sections.append(section)
                if len(keyword_sections) >= 5:
                    break

    parts = [head]
    for section in keyword_sections:
        if section not in head and section not in tail:
            parts.append(f"\n[...]\n{section}\n[...]\n")
    parts.append(tail)

    return "".join(parts)


async def llm_extract(html: str, schema: dict) -> tuple[dict, float]:
    """
    Extract structured data from HTML using Claude Haiku.

    Args:
        html: Cleaned HTML content (will be truncated if too long).
        schema: JSON Schema describing the fields to extract.

    Returns:
        (data, confidence) tuple where confidence is based on non-null required fields.
    """
    import anthropic  # type: ignore[import]

    truncated = _truncate_html(html, schema)
    schema_str = orjson.dumps(schema).decode()

    client = anthropic.AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    message = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2000,
        system=(
            "You are a structured data extractor. Given HTML content and a JSON Schema, "
            "extract data matching the schema. Return ONLY valid JSON matching the schema. "
            "If a field cannot be determined from the content, use null. "
            "Do not hallucinate data that isn't present in the content."
        ),
        messages=[
            {
                "role": "user",
                "content": (
                    f"Schema:\n{schema_str}\n\n"
                    f"HTML Content:\n{truncated}\n\n"
                    "Extract the data matching the schema. Return only the JSON object."
                ),
            }
        ],
    )

    raw_text = message.content[0].text.strip()

    # Strip markdown code fences if present
    if raw_text.startswith("```"):
        raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text, flags=re.MULTILINE)
        raw_text = re.sub(r"\s*```$", "", raw_text, flags=re.MULTILINE)
        raw_text = raw_text.strip()

    try:
        data = orjson.loads(raw_text)
    except Exception:
        # Try to extract JSON from the response
        json_match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        if json_match:
            data = orjson.loads(json_match.group())
        else:
            data = {}

    confidence = _compute_llm_confidence(data, schema)
    return data, confidence


def _compute_llm_confidence(data: dict, schema: dict) -> float:
    """Confidence = non-null required fields / total required fields."""
    required = schema.get("required", [])
    if not required:
        fields = list(schema.get("properties", {}).keys())
        if not fields:
            return 0.5
        matched = sum(1 for f in fields if data.get(f) is not None)
        return matched / len(fields)
    matched = sum(1 for f in required if data.get(f) is not None)
    return matched / len(required)
