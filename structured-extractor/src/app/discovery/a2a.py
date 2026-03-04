"""
Google A2A agent card — served at /.well-known/agent-card.json.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import ORJSONResponse

sys.path.insert(0, str(Path(__file__).parents[5]))
from shared.a2a_card import generate_a2a_card

router = APIRouter()

_TOOLS = [
    {"name": "extract", "description": "Extract structured data from a URL matching a JSON Schema"},
    {"name": "extract_from_html", "description": "Extract from raw HTML — no fetch required"},
    {"name": "extract_from_image", "description": "Extract from image URL using vision LLM"},
    {"name": "extract_batch", "description": "Batch extract from up to 50 URLs"},
    {"name": "list_capabilities", "description": "List extraction types and pricing (free)"},
]

_PRICING = {
    "extract (HTML-only)": "$0.005/request",
    "extract (JS-rendered)": "$0.015/request (coming soon)",
    "extract_from_html": "$0.003/request",
    "extract_from_image": "$0.020/request",
    "extract_batch": "$0.004/URL",
    "list_capabilities": "free",
    "cached result": "50% of standard price",
}


@router.get("/.well-known/agent-card.json")
async def agent_card() -> ORJSONResponse:
    base_url = os.environ.get("BASE_URL", "https://mcp-bank-extractor.fly.dev")
    card = generate_a2a_card(
        name="Structured Extractor",
        description=(
            "Extract structured JSON from any URL, raw HTML, or image using a JSON Schema. "
            "CSS/heuristic extraction first (JSON-LD, OpenGraph, microdata, CSS patterns). "
            "Falls back to Claude Haiku LLM when heuristics fail. "
            "x402-paid via USDC on Base. No signup required."
        ),
        base_url=base_url,
        tools=_TOOLS,
        pricing=_PRICING,
        version="1.0.0",
    )
    return ORJSONResponse(card)
