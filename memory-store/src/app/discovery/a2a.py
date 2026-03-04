"""
Google A2A agent card endpoint.
Served at /.well-known/agent-card.json
"""

import os
import sys

# Include shared module path — local dev or Docker container
for _shared_path in ["/shared", "/Volumes/2TB/projects/mcp-bank/shared"]:
    if _shared_path not in sys.path:
        sys.path.insert(0, _shared_path)
from a2a_card import generate_a2a_card  # noqa: E402

from fastapi import APIRouter

router = APIRouter()

_TOOLS = [
    {
        "name": "memory_set",
        "description": "Store a value in persistent agent memory with optional TTL.",
        "input_schema": {
            "type": "object",
            "properties": {
                "namespace": {"type": "string"},
                "key": {"type": "string"},
                "value": {"type": "string"},
                "ttl_seconds": {"type": "integer"},
            },
            "required": ["namespace", "key", "value"],
        },
    },
    {
        "name": "memory_get",
        "description": "Retrieve a stored value by exact key.",
        "input_schema": {
            "type": "object",
            "properties": {
                "namespace": {"type": "string"},
                "key": {"type": "string"},
            },
            "required": ["namespace", "key"],
        },
    },
    {
        "name": "memory_search",
        "description": "Semantic search over stored values using vector similarity.",
        "input_schema": {
            "type": "object",
            "properties": {
                "namespace": {"type": "string"},
                "query": {"type": "string"},
                "top_k": {"type": "integer", "default": 5},
                "min_score": {"type": "number", "default": 0.0},
            },
            "required": ["namespace", "query"],
        },
    },
    {
        "name": "memory_list",
        "description": "List keys in a namespace with optional prefix filtering.",
        "input_schema": {
            "type": "object",
            "properties": {
                "namespace": {"type": "string"},
                "prefix": {"type": "string"},
                "limit": {"type": "integer", "default": 100},
                "cursor": {"type": "string"},
            },
            "required": ["namespace"],
        },
    },
    {
        "name": "memory_delete",
        "description": "Delete a key from persistent memory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "namespace": {"type": "string"},
                "key": {"type": "string"},
            },
            "required": ["namespace", "key"],
        },
    },
    {
        "name": "memory_stats",
        "description": "Get usage statistics and cost information for a namespace (free).",
        "input_schema": {
            "type": "object",
            "properties": {
                "namespace": {"type": "string"},
            },
            "required": ["namespace"],
        },
    },
]

_PRICING = {
    "memory_set": "$0.001/call",
    "memory_get": "$0.0001/call",
    "memory_search": "$0.01/call",
    "memory_list": "$0.0001/call",
    "memory_delete": "$0.0001/call",
    "memory_stats": "free",
}


@router.get("/.well-known/agent-card.json")
async def agent_card() -> dict:
    base_url = os.environ.get("BASE_URL", "https://mcp-bank-memory.fly.dev")
    return generate_a2a_card(
        name="mcp-bank Memory Store",
        description=(
            "Hosted persistent memory for AI agents. "
            "Cross-session, cross-agent key-value storage with semantic vector search. "
            "Pay per operation via x402 (USDC on Base). No signup required."
        ),
        base_url=base_url,
        tools=_TOOLS,
        pricing=_PRICING,
        version="1.0.0",
    )
