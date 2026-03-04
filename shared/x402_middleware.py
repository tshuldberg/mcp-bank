"""
Shared x402 payment middleware pattern for all mcp-bank services.

Usage:
    from shared.x402_middleware import configure_x402

    configure_x402(app, pricing={
        "POST /memory/set": {"amount": "0.001", "currency": "USDC", "network": "base"},
    })
"""

import os
from typing import Callable
from fastapi import FastAPI, Request, Response
from x402.fastapi import x402_middleware


def configure_x402(app: FastAPI, pricing: dict[str, dict]) -> None:
    """
    Attach x402 payment middleware to a FastAPI app.

    Args:
        app: FastAPI application instance
        pricing: Dict mapping "METHOD /path" to payment config.
                 Each config: {"amount": str, "currency": "USDC", "network": "base"}
    """
    wallet_address = os.environ.get("WALLET_ADDRESS")
    if not wallet_address:
        raise ValueError("WALLET_ADDRESS environment variable is required")

    app.add_middleware(
        x402_middleware,
        wallet_address=wallet_address,
        pricing=pricing,
        facilitator_url=os.environ.get(
            "X402_FACILITATOR_URL",
            "https://x402.org/facilitator"
        ),
    )


def extract_agent_wallet(request: Request) -> str | None:
    """
    Extract the paying agent's wallet address from the x402 payment header.
    Use this for per-agent usage tracking and identity.
    """
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


# Standard pricing presets for reference
PRICING_PRESETS = {
    "memory": {
        "POST /memory/set":    {"amount": "0.001",  "currency": "USDC", "network": "base"},
        "POST /memory/get":    {"amount": "0.0001", "currency": "USDC", "network": "base"},
        "POST /memory/search": {"amount": "0.01",   "currency": "USDC", "network": "base"},
        "POST /memory/list":   {"amount": "0.0001", "currency": "USDC", "network": "base"},
        "POST /memory/delete": {"amount": "0.0001", "currency": "USDC", "network": "base"},
    },
    "transform": {
        "POST /transform":     {"amount": "0.001",  "currency": "USDC", "network": "base"},
        "POST /validate":      {"amount": "0.0005", "currency": "USDC", "network": "base"},
        "POST /infer_schema":  {"amount": "0.0005", "currency": "USDC", "network": "base"},
        "POST /reshape":       {"amount": "0.002",  "currency": "USDC", "network": "base"},
        "POST /diff":          {"amount": "0.001",  "currency": "USDC", "network": "base"},
        "POST /merge":         {"amount": "0.001",  "currency": "USDC", "network": "base"},
        "POST /filter":        {"amount": "0.001",  "currency": "USDC", "network": "base"},
        "POST /sample":        {"amount": "0.0005", "currency": "USDC", "network": "base"},
    },
    "executor": {
        "POST /execute":       {"amount": "0.001",  "currency": "USDC", "network": "base"},
        "POST /install":       {"amount": "0.005",  "currency": "USDC", "network": "base"},
    },
}
