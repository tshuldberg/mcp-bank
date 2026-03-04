"""
Health check endpoint — always free, no x402 required.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "service": "mcp-bank-memory-store",
        "version": "1.0.0",
    }
