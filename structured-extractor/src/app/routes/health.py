"""
Health check endpoint — always free, no auth required.
"""

from fastapi import APIRouter
from fastapi.responses import ORJSONResponse

router = APIRouter()


@router.get("/health")
async def health() -> ORJSONResponse:
    return ORJSONResponse({
        "status": "ok",
        "service": "mcp-bank-structured-extractor",
        "version": "1.0.0",
    })
