"""
Transform Agent — FastAPI application entry point.
"""

import os
import sys
from pathlib import Path

# Make shared/ importable from repo root
sys.path.insert(0, str(Path(__file__).parents[4]))

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.responses import ORJSONResponse

from src.app.routes.health import router as health_router
from src.app.routes.transform import router as transform_router
from src.app.discovery.mcp import router as mcp_router
from src.app.discovery.a2a import router as a2a_router

app = FastAPI(
    title="Transform Agent",
    description="Data format conversion and validation — x402-paid, MCP-native",
    version="1.0.0",
    default_response_class=ORJSONResponse,
)

# ─── Payment middleware ────────────────────────────────────────────────────────
# Only attach x402 when WALLET_ADDRESS is configured (skip in tests / dev without key)
_wallet = os.environ.get("WALLET_ADDRESS")
if _wallet:
    try:
        from shared.x402_middleware import configure_x402, PRICING_PRESETS
        configure_x402(app, pricing=PRICING_PRESETS["transform"])
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"x402 middleware not attached: {e}")

# ─── Routes ───────────────────────────────────────────────────────────────────
app.include_router(health_router)
app.include_router(transform_router)
app.include_router(mcp_router)
app.include_router(a2a_router)


@app.get("/", response_class=ORJSONResponse)
async def root() -> dict:
    return {
        "service": "transform-agent",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "capabilities": "/capabilities",
        "mcp": "/mcp",
        "agent_card": "/.well-known/agent-card.json",
    }
