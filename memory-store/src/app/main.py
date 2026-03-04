"""
mcp-bank Memory Store — FastAPI application entry point.

Startup order:
1. Load .env
2. Init Redis connection pool
3. Init asyncpg connection pool + ensure pgvector table
4. Attach x402 middleware
5. Register routes
"""

import os
import sys
from contextlib import asynccontextmanager

import asyncpg
import redis.asyncio as aioredis
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

# Make shared/ importable — local dev path or Docker container path
for _shared_path in ["/shared", "/Volumes/2TB/projects/mcp-bank/shared"]:
    if _shared_path not in sys.path:
        sys.path.insert(0, _shared_path)
from x402_middleware import configure_x402, PRICING_PRESETS  # noqa: E402

from .memory.store import RedisMemoryStore, VectorMemoryStore
from .routes import health, memory
from .discovery import mcp, a2a


# ─── Lifespan ─────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Redis
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    redis_client = aioredis.from_url(redis_url, decode_responses=False)
    app.state.redis_store = RedisMemoryStore(redis_client)

    # PostgreSQL + pgvector
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        pool = await asyncpg.create_pool(db_url, min_size=2, max_size=10)
        vector_store = VectorMemoryStore(pool)
        try:
            await vector_store.ensure_table()
        except Exception as e:
            print(f"[WARN] pgvector table init failed: {e}")
        app.state.vector_store = vector_store
        app.state.db_pool = pool
    else:
        # Stub vector store when DB not configured (dev without postgres)
        app.state.vector_store = _StubVectorStore()
        app.state.db_pool = None

    yield

    # Shutdown
    await redis_client.aclose()
    if app.state.db_pool:
        await app.state.db_pool.close()


# ─── Stub for dev without postgres ────────────────────────────────────────────


class _StubVectorStore:
    """No-op vector store used when DATABASE_URL is not set."""

    async def store_embedding(self, **_) -> None:
        pass

    async def delete_embedding(self, **_) -> None:
        pass

    async def search(self, namespace, query, top_k=5, min_score=0.0):
        return []


# ─── App ──────────────────────────────────────────────────────────────────────


app = FastAPI(
    title="mcp-bank Memory Store",
    description=(
        "Hosted persistent memory for AI agents. "
        "Cross-session key-value storage with semantic vector search. "
        "Pay per operation via x402 (USDC on Base)."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow all origins (agents call from anywhere)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# x402 payment middleware — attaches to billable routes
wallet = os.environ.get("WALLET_ADDRESS")
if wallet:
    configure_x402(app, pricing=PRICING_PRESETS["memory"])

# Routes
app.include_router(health.router)
app.include_router(memory.router)
app.include_router(mcp.router)
app.include_router(a2a.router)
