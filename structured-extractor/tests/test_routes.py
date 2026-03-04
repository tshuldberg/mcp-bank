"""
Integration tests for HTTP routes via httpx.AsyncClient.
All external HTTP calls and LLM API calls are mocked.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

# Ensure shared/ and project root are importable and WALLET_ADDRESS is absent (skip x402)
sys.path.insert(0, str(Path(__file__).parents[2]))
sys.path.insert(0, str(Path(__file__).parents[1]))
import os
os.environ.pop("WALLET_ADDRESS", None)

from src.app.main import app
from src.app.models.schemas import BatchExtractionResult, ExtractionResult

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _make_result(url: str | None = "https://example.com", method: str = "json_ld") -> ExtractionResult:
    return ExtractionResult(
        data={"title": "Test Product", "price": 29.99},
        confidence=0.95,
        method=method,
        url=url,
        extracted_at=datetime.now(timezone.utc).isoformat(),
        duration_ms=120,
        cached=False,
    )


def _make_batch_result(urls: list[str]) -> BatchExtractionResult:
    results = [_make_result(url) for url in urls]
    return BatchExtractionResult(
        results=results,
        total_urls=len(urls),
        successful=len(urls),
        failed=0,
        total_duration_ms=500,
    )


SIMPLE_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "price": {"type": "number"},
    },
    "required": ["title", "price"],
}

# ──────────────────────────────────────────────────────────────────────────────
# Health
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "mcp-bank-structured-extractor"


# ──────────────────────────────────────────────────────────────────────────────
# Capabilities
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_capabilities():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/capabilities")
    assert resp.status_code == 200
    data = resp.json()
    assert "extraction_types" in data
    assert "extract" in data["extraction_types"]
    assert "payment" in data


# ──────────────────────────────────────────────────────────────────────────────
# POST /extract
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_extract_valid_url():
    mock_result = _make_result()

    with patch("src.app.routes.extraction.pipeline.extract", AsyncMock(return_value=mock_result)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/extract", json={
                "url": "https://example.com/product",
                "schema": SIMPLE_SCHEMA,
            })

    assert resp.status_code == 200
    data = resp.json()
    assert data["confidence"] == 0.95
    assert data["method"] == "json_ld"
    assert data["data"]["title"] == "Test Product"


@pytest.mark.asyncio
async def test_extract_fetch_error():
    with patch(
        "src.app.routes.extraction.pipeline.extract",
        AsyncMock(side_effect=ValueError("Request timed out")),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/extract", json={
                "url": "https://bad-url.example.com",
                "schema": SIMPLE_SCHEMA,
            })

    assert resp.status_code == 422
    assert "error" in resp.json()


@pytest.mark.asyncio
async def test_extract_render_js_not_implemented():
    with patch(
        "src.app.routes.extraction.pipeline.extract",
        AsyncMock(side_effect=NotImplementedError("JS rendering not available")),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/extract", json={
                "url": "https://example.com",
                "schema": SIMPLE_SCHEMA,
                "render_js": True,
            })

    assert resp.status_code == 501


# ──────────────────────────────────────────────────────────────────────────────
# POST /extract/html
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_extract_from_html():
    mock_result = _make_result(url=None, method="css_heuristic")

    with patch(
        "src.app.routes.extraction.pipeline.extract_from_html",
        AsyncMock(return_value=mock_result),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/extract/html", json={
                "html": "<html><body><h1>Product</h1></body></html>",
                "schema": SIMPLE_SCHEMA,
            })

    assert resp.status_code == 200
    data = resp.json()
    assert data["method"] == "css_heuristic"


# ──────────────────────────────────────────────────────────────────────────────
# POST /extract/image
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_extract_from_image():
    mock_result = _make_result(url="https://example.com/image.png", method="vision_llm")

    with patch(
        "src.app.routes.extraction.pipeline.extract_from_image",
        AsyncMock(return_value=mock_result),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/extract/image", json={
                "image_url": "https://example.com/image.png",
                "schema": SIMPLE_SCHEMA,
            })

    assert resp.status_code == 200
    data = resp.json()
    assert data["method"] == "vision_llm"


@pytest.mark.asyncio
async def test_extract_from_image_fetch_error():
    with patch(
        "src.app.routes.extraction.pipeline.extract_from_image",
        AsyncMock(side_effect=ValueError("Image too large")),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/extract/image", json={
                "image_url": "https://example.com/giant.png",
                "schema": SIMPLE_SCHEMA,
            })

    assert resp.status_code == 422


# ──────────────────────────────────────────────────────────────────────────────
# POST /extract/batch
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_extract_batch():
    urls = ["https://example.com/1", "https://example.com/2"]
    mock_result = _make_batch_result(urls)

    with patch(
        "src.app.routes.extraction.pipeline.extract_batch",
        AsyncMock(return_value=mock_result),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/extract/batch", json={
                "urls": urls,
                "schema": SIMPLE_SCHEMA,
            })

    assert resp.status_code == 200
    data = resp.json()
    assert data["total_urls"] == 2
    assert data["successful"] == 2
    assert data["failed"] == 0
    assert len(data["results"]) == 2


@pytest.mark.asyncio
async def test_extract_batch_too_many_urls():
    urls = [f"https://example.com/{i}" for i in range(51)]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.post("/extract/batch", json={
            "urls": urls,
            "schema": SIMPLE_SCHEMA,
        })

    assert resp.status_code == 422
    assert "50" in resp.json()["error"]


# ──────────────────────────────────────────────────────────────────────────────
# MCP endpoint
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_mcp_initialize():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.post("/mcp", json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {},
        })

    assert resp.status_code == 200
    data = resp.json()
    assert data["jsonrpc"] == "2.0"
    assert data["id"] == 1
    assert "protocolVersion" in data["result"]
    assert data["result"]["serverInfo"]["name"] == "structured-extractor"


@pytest.mark.asyncio
async def test_mcp_tools_list():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.post("/mcp", json={
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {},
        })

    assert resp.status_code == 200
    data = resp.json()
    tools = data["result"]["tools"]
    assert len(tools) == 5
    tool_names = [t["name"] for t in tools]
    assert "extract" in tool_names
    assert "extract_from_html" in tool_names
    assert "extract_from_image" in tool_names
    assert "extract_batch" in tool_names
    assert "list_capabilities" in tool_names


@pytest.mark.asyncio
async def test_mcp_unknown_method():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.post("/mcp", json={
            "jsonrpc": "2.0",
            "id": 3,
            "method": "unknown/method",
            "params": {},
        })

    assert resp.status_code == 200
    data = resp.json()
    assert "error" in data
    assert data["error"]["code"] == -32601


@pytest.mark.asyncio
async def test_mcp_tools_call_extract():
    mock_result = _make_result()

    with patch("src.app.discovery.mcp.pipeline.extract", AsyncMock(return_value=mock_result)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/mcp", json={
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {
                    "name": "extract",
                    "arguments": {
                        "url": "https://example.com",
                        "schema": SIMPLE_SCHEMA,
                    },
                },
            })

    assert resp.status_code == 200
    data = resp.json()
    assert "result" in data
    assert "content" in data["result"]


@pytest.mark.asyncio
async def test_mcp_manifest():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/.well-known/mcp.json")

    assert resp.status_code == 200
    data = resp.json()
    assert "name" in data
    assert "mcp_endpoint" in data


@pytest.mark.asyncio
async def test_a2a_agent_card():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/.well-known/agent-card.json")

    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Structured Extractor"
    assert "capabilities" in data
    assert "payment" in data
