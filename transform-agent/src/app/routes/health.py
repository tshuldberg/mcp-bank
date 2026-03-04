"""Health check endpoint."""

import time
from fastapi import APIRouter
from src.app.middleware.cache import _get_client

router = APIRouter()

_start_time = time.time()


@router.get("/health")
async def health() -> dict:
    redis_ok = False
    client = _get_client()
    if client:
        try:
            await client.ping()
            redis_ok = True
        except Exception:
            pass

    return {
        "status": "ok",
        "service": "transform-agent",
        "version": "1.0.0",
        "uptime_seconds": int(time.time() - _start_time),
        "redis": "connected" if redis_ok else "unavailable",
    }
