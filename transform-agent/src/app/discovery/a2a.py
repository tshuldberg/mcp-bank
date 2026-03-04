"""
Google A2A agent card — served at /.well-known/agent-card.json.
"""

import os
import sys
from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import ORJSONResponse

# shared module is at repo root
sys.path.insert(0, str(Path(__file__).parents[6]))
from shared.a2a_card import generate_a2a_card

router = APIRouter()

_TOOLS = [
    {"name": "transform",    "description": "Convert between 20+ data formats"},
    {"name": "validate",     "description": "Validate JSON against a JSON Schema"},
    {"name": "infer_schema", "description": "Generate a JSON Schema from sample data"},
    {"name": "reshape",      "description": "Restructure nested JSON with dot-notation mapping"},
    {"name": "diff",         "description": "Compare two datasets for changes"},
    {"name": "merge",        "description": "Join two tabular datasets on a key"},
    {"name": "filter",       "description": "Filter rows using simple expressions"},
    {"name": "sample",       "description": "Randomly sample rows from a dataset"},
    {"name": "capabilities", "description": "List all supported conversions (free)"},
]

_PRICING = {
    "transform (text)":  "$0.001/request",
    "transform (doc)":   "$0.005/request",
    "validate":          "$0.0005/request",
    "infer_schema":      "$0.0005/request",
    "reshape":           "$0.002/request",
    "diff":              "$0.001/request",
    "merge":             "$0.001/request",
    "filter":            "$0.001/request",
    "sample":            "$0.0005/request",
    "capabilities":      "free",
    "cached result":     "50% of standard price",
}


@router.get("/.well-known/agent-card.json")
async def agent_card() -> ORJSONResponse:
    base_url = os.environ.get("BASE_URL", "https://mcp-bank-transform.fly.dev")
    card = generate_a2a_card(
        name="Transform Agent",
        description=(
            "Stateless data format conversion and validation service. "
            "Supports 20+ format pairs: JSON↔CSV↔XML↔YAML↔TOML, HTML↔Markdown, "
            "PDF/XLSX/DOCX extraction, and encoding transforms. "
            "x402-paid via USDC on Base. No signup required."
        ),
        base_url=base_url,
        tools=_TOOLS,
        pricing=_PRICING,
        version="1.0.0",
    )
    return ORJSONResponse(card)
