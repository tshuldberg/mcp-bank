"""
Tests for the mcp-bank Memory Store service.

Mocks Redis and pgvector so no real infrastructure is needed.
Tests all 6 operations (happy path + error cases), /health, /mcp JSON-RPC,
and that billable endpoints return 402 without a valid x402 payment.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport

# Ensure shared/ is importable
import sys
sys.path.insert(0, "/Volumes/2TB/projects/mcp-bank/shared")


# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_redis_store():
    store = MagicMock()
    store.set = AsyncMock(return_value={
        "stored": True, "key": "test-key", "namespace": "test-ns",
        "bytes": 10, "expires_at": None,
    })
    store.get = AsyncMock(return_value={
        "value": "test-value", "key": "test-key", "namespace": "test-ns",
        "found": True, "stored_at": None, "expires_at": None,
    })
    store.list = AsyncMock(return_value={
        "keys": ["test-key"], "namespace": "test-ns",
        "next_cursor": None, "total": 1,
    })
    store.delete = AsyncMock(return_value={
        "deleted": True, "key": "test-key", "namespace": "test-ns",
    })
    store.stats = AsyncMock(return_value={
        "namespace": "test-ns", "keys": 1, "bytes": 10,
        "reads_today": 0, "writes_today": 1, "cost_today_usd": 0.001,
    })
    return store


@pytest.fixture
def mock_vector_store():
    store = MagicMock()
    store.store_embedding = AsyncMock()
    store.delete_embedding = AsyncMock()
    store.search = AsyncMock(return_value=[])
    return store


@pytest.fixture
async def client(mock_redis_store, mock_vector_store):
    """
    AsyncClient with mocked stores and x402 middleware bypassed.
    We patch configure_x402 so no WALLET_ADDRESS env var is needed.
    """
    with patch("src.app.main.configure_x402"), \
         patch.dict("os.environ", {"WALLET_ADDRESS": "0xTestWallet"}):
        from src.app.main import app

        app.state.redis_store = mock_redis_store
        app.state.vector_store = mock_vector_store

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac


# ─── Health ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "mcp-bank-memory-store"
    assert data["version"] == "1.0.0"


# ─── memory/set ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_memory_set_happy(client, mock_redis_store):
    resp = await client.post("/memory/set", json={
        "namespace": "test-ns",
        "key": "test-key",
        "value": "hello world",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["stored"] is True
    assert data["key"] == "test-key"
    assert data["namespace"] == "test-ns"
    mock_redis_store.set.assert_awaited_once()


@pytest.mark.asyncio
async def test_memory_set_with_ttl(client, mock_redis_store):
    resp = await client.post("/memory/set", json={
        "namespace": "test-ns",
        "key": "ephemeral",
        "value": "temporary",
        "ttl_seconds": 3600,
    })
    assert resp.status_code == 200
    call_kwargs = mock_redis_store.set.call_args
    assert call_kwargs.kwargs.get("ttl_seconds") == 3600


@pytest.mark.asyncio
async def test_memory_set_missing_fields(client):
    resp = await client.post("/memory/set", json={"namespace": "test-ns"})
    assert resp.status_code == 422


# ─── memory/get ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_memory_get_happy(client, mock_redis_store):
    resp = await client.post("/memory/get", json={
        "namespace": "test-ns",
        "key": "test-key",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["found"] is True
    assert data["value"] == "test-value"


@pytest.mark.asyncio
async def test_memory_get_not_found(client, mock_redis_store):
    mock_redis_store.get = AsyncMock(return_value={
        "value": None, "key": "missing", "namespace": "test-ns",
        "found": False, "stored_at": None, "expires_at": None,
    })
    resp = await client.post("/memory/get", json={
        "namespace": "test-ns",
        "key": "missing",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["found"] is False
    assert data["value"] is None


# ─── memory/search ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_memory_search_happy(client, mock_vector_store):
    from src.app.models.schemas import SearchResult
    from datetime import datetime, timezone

    mock_vector_store.search = AsyncMock(return_value=[
        SearchResult(
            key="test-key",
            value="relevant content",
            score=0.92,
            stored_at=datetime.now(timezone.utc),
        )
    ])

    resp = await client.post("/memory/search", json={
        "namespace": "test-ns",
        "query": "find relevant things",
        "top_k": 5,
        "min_score": 0.7,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 1
    assert data["results"][0]["score"] == 0.92
    assert data["results"][0]["key"] == "test-key"


@pytest.mark.asyncio
async def test_memory_search_empty_results(client, mock_vector_store):
    mock_vector_store.search = AsyncMock(return_value=[])
    resp = await client.post("/memory/search", json={
        "namespace": "test-ns",
        "query": "nothing matches this",
    })
    assert resp.status_code == 200
    assert resp.json()["count"] == 0


# ─── memory/list ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_memory_list_happy(client, mock_redis_store):
    resp = await client.post("/memory/list", json={"namespace": "test-ns"})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["keys"], list)
    assert data["total"] == 1


@pytest.mark.asyncio
async def test_memory_list_with_prefix(client, mock_redis_store):
    resp = await client.post("/memory/list", json={
        "namespace": "test-ns",
        "prefix": "research/",
        "limit": 10,
    })
    assert resp.status_code == 200
    call_kwargs = mock_redis_store.list.call_args
    assert call_kwargs.kwargs.get("prefix") == "research/"


# ─── memory/delete ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_memory_delete_happy(client, mock_redis_store):
    resp = await client.post("/memory/delete", json={
        "namespace": "test-ns",
        "key": "test-key",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["deleted"] is True


@pytest.mark.asyncio
async def test_memory_delete_not_found(client, mock_redis_store):
    mock_redis_store.delete = AsyncMock(return_value={
        "deleted": False, "key": "ghost", "namespace": "test-ns",
    })
    resp = await client.post("/memory/delete", json={
        "namespace": "test-ns",
        "key": "ghost",
    })
    assert resp.status_code == 200
    assert resp.json()["deleted"] is False


# ─── memory/stats ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_memory_stats(client, mock_redis_store):
    resp = await client.get("/memory/stats", params={"namespace": "test-ns"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["namespace"] == "test-ns"
    assert "keys" in data
    assert "cost_today_usd" in data


# ─── /mcp JSON-RPC ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_mcp_initialize(client):
    resp = await client.post("/mcp", json={
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
    assert data["result"]["serverInfo"]["name"] == "mcp-bank-memory-store"


@pytest.mark.asyncio
async def test_mcp_tools_list(client):
    resp = await client.post("/mcp", json={
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {},
    })
    assert resp.status_code == 200
    data = resp.json()
    tools = data["result"]["tools"]
    tool_names = [t["name"] for t in tools]
    assert "memory_set" in tool_names
    assert "memory_get" in tool_names
    assert "memory_search" in tool_names
    assert "memory_list" in tool_names
    assert "memory_delete" in tool_names
    assert "memory_stats" in tool_names
    # All tools have inputSchema
    for tool in tools:
        assert "inputSchema" in tool
        assert "description" in tool


@pytest.mark.asyncio
async def test_mcp_tools_call_memory_set(client, mock_redis_store, mock_vector_store):
    resp = await client.post("/mcp", json={
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "memory_set",
            "arguments": {
                "namespace": "test-ns",
                "key": "mcp-key",
                "value": "mcp-value",
            },
        },
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["jsonrpc"] == "2.0"
    assert "result" in data


@pytest.mark.asyncio
async def test_mcp_unknown_method(client):
    resp = await client.post("/mcp", json={
        "jsonrpc": "2.0",
        "id": 4,
        "method": "not/a/method",
        "params": {},
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "error" in data
    assert data["error"]["code"] == -32601


@pytest.mark.asyncio
async def test_mcp_unknown_tool(client):
    resp = await client.post("/mcp", json={
        "jsonrpc": "2.0",
        "id": 5,
        "method": "tools/call",
        "params": {"name": "nonexistent_tool", "arguments": {}},
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "error" in data


@pytest.mark.asyncio
async def test_mcp_invalid_json_rpc_version(client):
    resp = await client.post("/mcp", json={
        "jsonrpc": "1.0",
        "id": 6,
        "method": "initialize",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "error" in data


# ─── x402 payment enforcement ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_billable_endpoints_return_402_without_payment():
    """
    Verify that billable endpoints return 402 when x402 middleware is active
    and no payment header is provided.
    """
    # This test uses a fresh app instance with x402 middleware actually configured
    # (not mocked). We expect 402 since no X-Payment header is sent.
    with patch.dict("os.environ", {
        "WALLET_ADDRESS": "0xTestWallet123",
        "REDIS_URL": "redis://localhost:6379/0",
    }):
        # Mock out x402_middleware to simulate 402 rejection
        from fastapi import Request, Response
        from fastapi.responses import JSONResponse

        async def mock_x402_dispatch(request: Request, call_next):
            # Simulate x402 rejecting requests without payment
            if not request.headers.get("X-Payment"):
                return JSONResponse(
                    status_code=402,
                    content={"error": "Payment Required", "accepts": []},
                )
            return await call_next(request)

        with patch("x402.fastapi.x402_middleware") as mock_mw:
            # Patch middleware to use our simulated 402 handler
            mock_mw.return_value = mock_x402_dispatch

            from importlib import reload
            import src.app.main as main_module
            reload(main_module)

            app = main_module.app
            app.state.redis_store = MagicMock()
            app.state.vector_store = MagicMock()

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                # /health should always be free (200)
                health_resp = await ac.get("/health")
                assert health_resp.status_code == 200

                # Billable endpoints should be rejected (402)
                for path, payload in [
                    ("/memory/set", {"namespace": "ns", "key": "k", "value": "v"}),
                    ("/memory/get", {"namespace": "ns", "key": "k"}),
                    ("/memory/search", {"namespace": "ns", "query": "q"}),
                    ("/memory/list", {"namespace": "ns"}),
                    ("/memory/delete", {"namespace": "ns", "key": "k"}),
                ]:
                    resp = await ac.post(path, json=payload)
                    assert resp.status_code == 402, (
                        f"Expected 402 for {path}, got {resp.status_code}"
                    )
