"""
Extraction route handlers — POST /extract, /extract/html, /extract/image, /extract/batch.
No business logic here: handlers call pipeline functions and log metering.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make shared/ importable
sys.path.insert(0, str(Path(__file__).parents[5]))

from fastapi import APIRouter, Request
from fastapi.responses import ORJSONResponse

from shared.errors import http_error
from shared.metering import log_operation


def extract_agent_wallet(request: Request) -> str | None:
    """Extract the paying agent's wallet address from the x402 payment header."""
    payment_header = request.headers.get("X-Payment", "")
    if not payment_header:
        return None
    try:
        import base64
        import json
        payload = json.loads(base64.b64decode(payment_header))
        return payload.get("from", None)
    except Exception:
        return None

from src.app.extraction import pipeline
from src.app.models.schemas import (
    BatchExtractionResult,
    ExtractBatchRequest,
    ExtractFromHtmlRequest,
    ExtractFromImageRequest,
    ExtractRequest,
    ExtractionResult,
)

router = APIRouter()

_SERVICE = "structured-extractor"

_PRICING = {
    "extract": 0.005,
    "extract_html": 0.003,
    "extract_image": 0.020,
    "extract_batch": 0.004,  # per URL
}


@router.post("/extract", response_model=ExtractionResult)
async def extract_url(body: ExtractRequest, request: Request) -> ORJSONResponse:
    """Extract structured data from a URL using the provided JSON Schema."""
    agent_wallet = extract_agent_wallet(request)

    try:
        result = await pipeline.extract(
            url=body.url,
            schema=body.schema_,
            render_js=body.render_js,
        )
    except NotImplementedError as e:
        return http_error(501, str(e), "NOT_IMPLEMENTED")
    except ValueError as e:
        return http_error(422, str(e), "FETCH_ERROR")
    except Exception as e:
        return http_error(500, f"Extraction failed: {e}", "EXTRACTION_ERROR")

    price = _PRICING["extract"] * (0.5 if result.cached else 1.0)
    await log_operation(
        service=_SERVICE,
        operation="extract",
        agent_wallet=agent_wallet,
        price_usd=price,
        duration_ms=result.duration_ms,
        cached=result.cached,
    )

    return ORJSONResponse(result.model_dump())


@router.post("/extract/html", response_model=ExtractionResult)
async def extract_from_html(body: ExtractFromHtmlRequest, request: Request) -> ORJSONResponse:
    """Extract structured data from raw HTML using the provided JSON Schema."""
    agent_wallet = extract_agent_wallet(request)

    try:
        result = await pipeline.extract_from_html(html=body.html, schema=body.schema_)
    except Exception as e:
        return http_error(500, f"Extraction failed: {e}", "EXTRACTION_ERROR")

    await log_operation(
        service=_SERVICE,
        operation="extract_html",
        agent_wallet=agent_wallet,
        price_usd=_PRICING["extract_html"],
        duration_ms=result.duration_ms,
        cached=False,
    )

    return ORJSONResponse(result.model_dump())


@router.post("/extract/image", response_model=ExtractionResult)
async def extract_from_image(body: ExtractFromImageRequest, request: Request) -> ORJSONResponse:
    """Extract structured data from an image URL using vision LLM."""
    agent_wallet = extract_agent_wallet(request)

    try:
        result = await pipeline.extract_from_image(
            image_url=body.image_url, schema=body.schema_
        )
    except ValueError as e:
        return http_error(422, str(e), "IMAGE_FETCH_ERROR")
    except Exception as e:
        return http_error(500, f"Image extraction failed: {e}", "EXTRACTION_ERROR")

    await log_operation(
        service=_SERVICE,
        operation="extract_image",
        agent_wallet=agent_wallet,
        price_usd=_PRICING["extract_image"],
        duration_ms=result.duration_ms,
        cached=False,
    )

    return ORJSONResponse(result.model_dump())


@router.post("/extract/batch", response_model=BatchExtractionResult)
async def extract_batch(body: ExtractBatchRequest, request: Request) -> ORJSONResponse:
    """Batch extract from multiple URLs using the provided JSON Schema."""
    if len(body.urls) > 50:
        return http_error(422, "Maximum 50 URLs per batch request", "TOO_MANY_URLS")

    agent_wallet = extract_agent_wallet(request)

    try:
        result = await pipeline.extract_batch(
            urls=body.urls,
            schema=body.schema_,
            render_js=body.render_js,
            max_concurrent=body.max_concurrent,
        )
    except Exception as e:
        return http_error(500, f"Batch extraction failed: {e}", "EXTRACTION_ERROR")

    price = _PRICING["extract_batch"] * result.total_urls
    await log_operation(
        service=_SERVICE,
        operation="extract_batch",
        agent_wallet=agent_wallet,
        price_usd=price,
        duration_ms=result.total_duration_ms,
        cached=False,
    )

    return ORJSONResponse(result.model_dump())


@router.get("/capabilities")
async def capabilities() -> ORJSONResponse:
    """List supported extraction types, pricing, and limits. Always free."""
    return ORJSONResponse({
        "extraction_types": {
            "extract": {
                "description": "Extract from URL (HTML-only). CSS/heuristic first, LLM fallback.",
                "price_usd": 0.005,
                "cached_price_usd": 0.0025,
            },
            "extract_render_js": {
                "description": "Extract from URL with JS rendering. (Coming soon — Playwright)",
                "price_usd": 0.015,
                "status": "planned",
            },
            "extract_html": {
                "description": "Extract from raw HTML string. No fetch required.",
                "price_usd": 0.003,
            },
            "extract_image": {
                "description": "Extract from image URL using vision LLM.",
                "price_usd": 0.020,
            },
            "extract_batch": {
                "description": "Batch extract from multiple URLs (max 50). Same schema for all.",
                "price_usd_per_url": 0.004,
                "max_urls": 50,
                "max_concurrent": 20,
            },
        },
        "extraction_methods": [
            "json_ld",
            "opengraph",
            "microdata",
            "css_heuristic",
            "llm_haiku",
            "vision_llm",
        ],
        "confidence_scoring": {
            "0.9-1.0": "JSON-LD or structured data, fully matched",
            "0.7-0.9": "CSS heuristics, most fields matched",
            "0.5-0.7": "LLM extraction, partial coverage",
            "0.3-0.5": "LLM extraction, low coverage",
            "<0.3": "Extraction largely failed",
        },
        "limits": {
            "batch_max_urls": 50,
            "max_concurrent": 20,
            "fetch_timeout_seconds": 15,
            "max_image_size_mb": 10,
        },
        "payment": {
            "protocol": "x402",
            "network": "base",
            "currency": "USDC",
        },
    })
