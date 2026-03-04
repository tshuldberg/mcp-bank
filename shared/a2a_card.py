"""
Shared Google A2A agent card generator for all mcp-bank services.

Each service calls generate_a2a_card() with its own metadata.
The card is served at /.well-known/agent-card.json.
"""

from typing import Any


def generate_a2a_card(
    name: str,
    description: str,
    base_url: str,
    tools: list[dict[str, Any]],
    pricing: dict[str, str],
    version: str = "1.0.0",
) -> dict:
    """
    Generate a Google A2A agent card.

    Args:
        name: Human-readable service name
        description: What this agent does
        base_url: Base URL of the deployed service
        tools: List of tool descriptors (name, description, input_schema)
        pricing: Dict of operation → price string
        version: Service version

    Returns:
        A2A agent card as a dict (serve as JSON at /.well-known/agent-card.json)
    """
    return {
        "schema_version": "1.0",
        "name": name,
        "description": description,
        "version": version,
        "url": base_url,
        "provider": {
            "name": "mcp-bank",
            "url": "https://github.com/tshuldberg/mcp-bank",
        },
        "capabilities": {
            "tools": tools,
        },
        "endpoints": {
            "mcp": f"{base_url}/mcp",
            "openapi": f"{base_url}/openapi.json",
            "health": f"{base_url}/health",
        },
        "payment": {
            "protocol": "x402",
            "network": "base",
            "currency": "USDC",
            "pricing": pricing,
            "facilitator": "https://x402.org/facilitator",
        },
        "authentication": {
            "type": "x402_wallet",
            "description": "No signup required. Pay per request via x402 (USDC on Base).",
        },
        "discovery": {
            "smithery": True,
            "mcp_so": True,
        },
    }
