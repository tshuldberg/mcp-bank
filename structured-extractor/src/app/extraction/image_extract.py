"""
Vision-based extraction — uses Claude Haiku with vision to extract
structured data from images (screenshots, product photos, etc.).
"""

from __future__ import annotations

import base64
import os
import re

import httpx
import orjson

_MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB


async def image_extract(image_url: str, schema: dict) -> tuple[dict, float]:
    """
    Extract structured data from an image using Claude Haiku vision.

    Args:
        image_url: URL of the image to analyze.
        schema: JSON Schema describing the fields to extract.

    Returns:
        (data, confidence) tuple.

    Raises:
        ValueError: If the image is too large or cannot be fetched.
    """
    import anthropic  # type: ignore[import]

    # Download image
    async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
        try:
            response = await client.get(image_url)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise ValueError(f"Failed to fetch image ({e.response.status_code}): {image_url}")
        except httpx.RequestError as e:
            raise ValueError(f"Failed to fetch image: {e}")

    image_bytes = response.content
    if len(image_bytes) > _MAX_IMAGE_BYTES:
        raise ValueError(
            f"Image too large: {len(image_bytes) / 1024 / 1024:.1f}MB (max 10MB)"
        )

    # Detect media type from content-type header or URL
    content_type = response.headers.get("content-type", "image/jpeg")
    media_type = content_type.split(";")[0].strip()
    if media_type not in ("image/jpeg", "image/png", "image/gif", "image/webp"):
        media_type = "image/jpeg"  # default fallback

    image_b64 = base64.standard_b64encode(image_bytes).decode()
    schema_str = orjson.dumps(schema).decode()

    ai_client = anthropic.AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    message = await ai_client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2000,
        system=(
            "You are a structured data extractor. Extract data from the provided image "
            "matching the given JSON Schema. Return ONLY valid JSON matching the schema. "
            "If a field cannot be determined from the image, use null."
        ),
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": (
                            f"Schema:\n{schema_str}\n\n"
                            "Extract the data matching the schema from this image. "
                            "Return only the JSON object."
                        ),
                    },
                ],
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
        json_match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        if json_match:
            data = orjson.loads(json_match.group())
        else:
            data = {}

    confidence = _compute_confidence(data, schema)
    return data, confidence


def _compute_confidence(data: dict, schema: dict) -> float:
    required = schema.get("required", [])
    if not required:
        fields = list(schema.get("properties", {}).keys())
        if not fields:
            return 0.5
        matched = sum(1 for f in fields if data.get(f) is not None)
        return matched / len(fields)
    matched = sum(1 for f in required if data.get(f) is not None)
    return matched / len(required)
