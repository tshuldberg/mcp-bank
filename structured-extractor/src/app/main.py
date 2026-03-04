"""
mcp-bank Structured Extractor — FastAPI application entry point.
"""

from __future__ import annotations

import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Make shared/ importable from repo root
sys.path.insert(0, str(Path(__file__).parents[4]))

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from src.app.routes.health import router as health_router
from src.app.routes.extraction import router as extraction_router
from src.app.discovery.mcp import router as mcp_router
from src.app.discovery.a2a import router as a2a_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Init Redis connection (graceful — service works without it)
    redis_url = os.environ.get("REDIS_URL")
    if redis_url:
        try:
            from src.app.middleware.cache import _get_client
            client = _get_client()
            if client:
                await client.ping()
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Redis unavailable (cache disabled): {e}")

    yield

    # Cleanup Redis connection on shutdown
    from src.app.middleware import cache as cache_mod
    if cache_mod._redis is not None:
        try:
            await cache_mod._redis.aclose()
        except Exception:
            pass


app = FastAPI(
    title="mcp-bank Structured Extractor",
    description=(
        "Extract structured JSON from any URL, HTML, or image using a JSON Schema. "
        "CSS/heuristic extraction first, LLM fallback. x402-paid, MCP-native."
    ),
    version="1.0.0",
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
)

# ─── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Payment middleware ────────────────────────────────────────────────────────
# Only attach x402 when WALLET_ADDRESS is configured (skip in tests / dev without key)
_wallet = os.environ.get("WALLET_ADDRESS")
if _wallet:
    try:
        from shared.x402_middleware import configure_x402

        configure_x402(app, pricing={
            "POST /extract":        {"amount": "0.005",  "currency": "USDC", "network": "base"},
            "POST /extract/html":   {"amount": "0.003",  "currency": "USDC", "network": "base"},
            "POST /extract/image":  {"amount": "0.020",  "currency": "USDC", "network": "base"},
            "POST /extract/batch":  {"amount": "0.020",  "currency": "USDC", "network": "base"},
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"x402 middleware not attached: {e}")

# ─── Routes ───────────────────────────────────────────────────────────────────
app.include_router(health_router)
app.include_router(extraction_router)
app.include_router(mcp_router)
app.include_router(a2a_router)


@app.get("/", response_class=ORJSONResponse)
async def root() -> dict:
    return {
        "service": "mcp-bank-structured-extractor",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "capabilities": "/capabilities",
        "mcp": "/mcp",
        "agent_card": "/.well-known/agent-card.json",
        "mcp_manifest": "/.well-known/mcp.json",
    }
