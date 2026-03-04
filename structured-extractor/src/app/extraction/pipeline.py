"""
Main extraction pipeline orchestrator.
Coordinates fetching, cleaning, fast extraction, and LLM fallback.
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone

import orjson

from src.app.extraction.cleaner import clean_html
from src.app.extraction.fast_extract import fast_extract
from src.app.extraction.fetcher import fetch_html
from src.app.extraction.image_extract import image_extract
from src.app.extraction.llm_extract import llm_extract
from src.app.middleware.cache import cache_get, cache_set, make_cache_key
from src.app.models.schemas import BatchExtractionResult, ExtractionResult

_FAST_CONFIDENCE_THRESHOLD = 0.8


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _validate_against_schema(data: dict, schema: dict) -> dict:
    """
    Validate data against JSON Schema, filling missing optional fields with null.
    Returns the (possibly augmented) data dict.
    """
    try:
        import jsonschema  # type: ignore[import]

        # Fill missing optional fields with null before validation
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        for field in properties:
            if field not in data:
                data[field] = None

        jsonschema.validate(instance=data, schema=schema)
    except Exception:
        # Partial/invalid extraction — still return whatever we got
        pass
    return data


async def extract(url: str, schema: dict, render_js: bool = False) -> ExtractionResult:
    """
    Full extraction pipeline: fetch → clean → fast extract → LLM fallback → validate.

    Checks cache first and writes result to cache after successful extraction.
    """
    t0 = time.monotonic()

    schema_json = orjson.dumps(schema, option=orjson.OPT_SORT_KEYS).decode()
    cache_key = make_cache_key(url, schema_json, render_js)

    # 1. Cache check
    cached_raw = await cache_get(cache_key)
    if cached_raw:
        result = ExtractionResult.model_validate(orjson.loads(cached_raw))
        result.cached = True
        return result

    # 2. Fetch
    html = await fetch_html(url, render_js=render_js)

    # 3. Clean
    clean = clean_html(html)

    # 4. Fast extraction
    data, confidence, method = fast_extract(clean, schema)

    # 5. LLM fallback if confidence below threshold
    if confidence < _FAST_CONFIDENCE_THRESHOLD:
        data, confidence = await llm_extract(clean, schema)
        method = "llm_haiku"

    # 6. Validate + fill nulls
    if data is not None:
        data = _validate_against_schema(data, schema)

    duration_ms = int((time.monotonic() - t0) * 1000)

    result = ExtractionResult(
        data=data,
        confidence=round(confidence, 4),
        method=method,
        url=url,
        extracted_at=_now_iso(),
        duration_ms=duration_ms,
        cached=False,
    )

    # 7. Cache result
    await cache_set(cache_key, orjson.dumps(result.model_dump()).decode())

    return result


async def extract_from_html(html: str, schema: dict) -> ExtractionResult:
    """
    Extract from raw HTML — skip fetch step.
    """
    t0 = time.monotonic()

    clean = clean_html(html)
    data, confidence, method = fast_extract(clean, schema)

    if confidence < _FAST_CONFIDENCE_THRESHOLD:
        data, confidence = await llm_extract(clean, schema)
        method = "llm_haiku"

    if data is not None:
        data = _validate_against_schema(data, schema)

    duration_ms = int((time.monotonic() - t0) * 1000)

    return ExtractionResult(
        data=data,
        confidence=round(confidence, 4),
        method=method,
        url=None,
        extracted_at=_now_iso(),
        duration_ms=duration_ms,
        cached=False,
    )


async def extract_from_image(image_url: str, schema: dict) -> ExtractionResult:
    """
    Extract structured data from an image URL using vision LLM.
    """
    t0 = time.monotonic()

    data, confidence = await image_extract(image_url, schema)

    if data is not None:
        data = _validate_against_schema(data, schema)

    duration_ms = int((time.monotonic() - t0) * 1000)

    return ExtractionResult(
        data=data,
        confidence=round(confidence, 4),
        method="vision_llm",
        url=image_url,
        extracted_at=_now_iso(),
        duration_ms=duration_ms,
        cached=False,
    )


async def extract_batch(
    urls: list[str],
    schema: dict,
    render_js: bool,
    max_concurrent: int,
) -> BatchExtractionResult:
    """
    Batch extraction from multiple URLs using a concurrency semaphore.
    """
    t0 = time.monotonic()
    semaphore = asyncio.Semaphore(max_concurrent)

    async def _extract_one(url: str) -> ExtractionResult:
        async with semaphore:
            try:
                return await extract(url, schema, render_js=render_js)
            except Exception as e:
                return ExtractionResult(
                    data=None,
                    confidence=0.0,
                    method="error",
                    url=url,
                    extracted_at=_now_iso(),
                    duration_ms=0,
                    cached=False,
                )

    results = await asyncio.gather(*[_extract_one(url) for url in urls])

    successful = sum(1 for r in results if r.data is not None)
    failed = len(results) - successful
    total_duration_ms = int((time.monotonic() - t0) * 1000)

    return BatchExtractionResult(
        results=list(results),
        total_urls=len(urls),
        successful=successful,
        failed=failed,
        total_duration_ms=total_duration_ms,
    )
