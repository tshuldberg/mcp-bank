"""
Integration tests for Transform Agent routes via httpx.AsyncClient.
x402 middleware is bypassed (WALLET_ADDRESS not set in test env).
"""

import pytest
import orjson
from httpx import AsyncClient, ASGITransport


@pytest.fixture
def app():
    import os
    # Ensure no wallet address so x402 middleware is not attached
    os.environ.pop("WALLET_ADDRESS", None)
    from src.app.main import app
    return app


@pytest.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# ─── Health ───────────────────────────────────────────────────────────────────

async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["service"] == "transform-agent"


# ─── Root ─────────────────────────────────────────────────────────────────────

async def test_root(client):
    r = await client.get("/")
    assert r.status_code == 200
    assert "capabilities" in r.json()


# ─── Capabilities (free) ──────────────────────────────────────────────────────

async def test_capabilities(client):
    r = await client.get("/capabilities")
    assert r.status_code == 200
    data = r.json()
    assert "conversions" in data
    assert data["total_conversions"] > 10


# ─── Transform ────────────────────────────────────────────────────────────────

async def test_transform_json_to_csv(client):
    r = await client.post("/transform", json={
        "source_format": "json",
        "target_format": "csv",
        "data": '[{"name":"Alice","age":30}]',
    })
    assert r.status_code == 200
    data = r.json()
    assert "Alice" in data["result"]
    assert data["source_format"] == "json"
    assert data["target_format"] == "csv"
    assert "duration_ms" in data
    assert "cached" in data


async def test_transform_csv_to_json(client):
    r = await client.post("/transform", json={
        "source_format": "csv",
        "target_format": "json",
        "data": "name,age\nAlice,30\nBob,25\n",
    })
    assert r.status_code == 200
    rows = orjson.loads(r.json()["result"])
    assert len(rows) == 2


async def test_transform_html_to_markdown(client):
    r = await client.post("/transform", json={
        "source_format": "html",
        "target_format": "markdown",
        "data": "<h1>Hello</h1><p>World</p>",
    })
    assert r.status_code == 200
    assert "# Hello" in r.json()["result"]


async def test_transform_unsupported(client):
    r = await client.post("/transform", json={
        "source_format": "json",
        "target_format": "docx",
        "data": "{}",
    })
    assert r.status_code == 422


async def test_transform_base64(client):
    r = await client.post("/transform", json={
        "source_format": "json",
        "target_format": "base64",
        "data": '{"key":"value"}',
    })
    assert r.status_code == 200
    import base64
    decoded = base64.b64decode(r.json()["result"]).decode()
    assert "key" in decoded


# ─── Validate ─────────────────────────────────────────────────────────────────

async def test_validate_valid(client):
    r = await client.post("/validate", json={
        "data": '{"name":"Alice","age":30}',
        "schema": '{"type":"object","properties":{"name":{"type":"string"},"age":{"type":"integer"}},"required":["name","age"]}',
    })
    assert r.status_code == 200
    data = r.json()
    assert data["valid"] is True
    assert data["errors"] == []


async def test_validate_invalid(client):
    r = await client.post("/validate", json={
        "data": '{"name":"Alice","age":"thirty"}',
        "schema": '{"type":"object","properties":{"age":{"type":"integer"}},"required":["name","age"]}',
    })
    assert r.status_code == 200
    data = r.json()
    assert data["valid"] is False
    assert len(data["errors"]) > 0


# ─── Infer schema ─────────────────────────────────────────────────────────────

async def test_infer_schema(client):
    r = await client.post("/infer_schema", json={
        "data": '[{"name":"Alice","age":30},{"name":"Bob","age":25}]',
    })
    assert r.status_code == 200
    data = r.json()
    assert "schema" in data
    assert data["schema"]["type"] == "array"
    assert data["confidence"] > 0


# ─── Reshape ──────────────────────────────────────────────────────────────────

async def test_reshape(client):
    r = await client.post("/reshape", json={
        "data": {"user": {"profile": {"name": "Alice"}, "address": {"city": "Paris"}}},
        "mapping": {"name": "user.profile.name", "city": "user.address.city"},
    })
    assert r.status_code == 200
    data = r.json()
    assert data["result"]["name"] == "Alice"
    assert data["result"]["city"] == "Paris"
    assert data["fields_mapped"] == 2


# ─── Diff ─────────────────────────────────────────────────────────────────────

async def test_diff(client):
    r = await client.post("/diff", json={
        "before": '[{"id":1,"status":"active"},{"id":2,"status":"active"}]',
        "after":  '[{"id":1,"status":"inactive"},{"id":3,"status":"active"}]',
        "key_field": "id",
    })
    assert r.status_code == 200
    data = r.json()
    assert len(data["added"]) == 1
    assert len(data["removed"]) == 1
    assert len(data["modified"]) == 1


# ─── Merge ────────────────────────────────────────────────────────────────────

async def test_merge(client):
    r = await client.post("/merge", json={
        "left":  '[{"id":1,"name":"Alice"}]',
        "right": '[{"id":1,"city":"Paris"}]',
        "on": "id",
        "how": "inner",
    })
    assert r.status_code == 200
    data = r.json()
    rows = orjson.loads(data["result"])
    assert rows[0]["name"] == "Alice"
    assert rows[0]["city"] == "Paris"
    assert data["rows_out"] == 1


# ─── Filter ───────────────────────────────────────────────────────────────────

async def test_filter(client):
    r = await client.post("/filter", json={
        "data": '[{"name":"Alice","age":30},{"name":"Bob","age":17}]',
        "where": "age >= 18",
    })
    assert r.status_code == 200
    data = r.json()
    rows = orjson.loads(data["result"])
    assert len(rows) == 1
    assert rows[0]["name"] == "Alice"
    assert data["rows_in"] == 2
    assert data["rows_out"] == 1


# ─── Sample ───────────────────────────────────────────────────────────────────

async def test_sample(client):
    import orjson as oj
    big_data = oj.dumps([{"id": i, "val": i * 2} for i in range(50)]).decode()
    r = await client.post("/sample", json={
        "data": big_data,
        "n": 5,
        "seed": 123,
    })
    assert r.status_code == 200
    data = r.json()
    rows = orjson.loads(data["result"])
    assert len(rows) == 5
    assert data["rows_in"] == 50


# ─── MCP endpoint ─────────────────────────────────────────────────────────────

async def test_mcp_initialize(client):
    r = await client.post("/mcp", json={
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {},
    })
    assert r.status_code == 200
    data = r.json()
    assert data["result"]["protocolVersion"] == "2024-11-05"
    assert data["result"]["serverInfo"]["name"] == "transform-agent"


async def test_mcp_tools_list(client):
    r = await client.post("/mcp", json={
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {},
    })
    assert r.status_code == 200
    tools = r.json()["result"]["tools"]
    tool_names = [t["name"] for t in tools]
    assert "transform" in tool_names
    assert "validate" in tool_names
    assert "capabilities" in tool_names
    assert len(tools) == 9


async def test_mcp_tool_call_transform(client):
    r = await client.post("/mcp", json={
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "transform",
            "arguments": {
                "source_format": "json",
                "target_format": "csv",
                "data": '[{"a":1,"b":2}]',
            },
        },
    })
    assert r.status_code == 200
    content = r.json()["result"]["content"]
    result = orjson.loads(content[0]["text"])
    assert "a" in result["result"]


async def test_mcp_tool_call_capabilities(client):
    r = await client.post("/mcp", json={
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {"name": "capabilities", "arguments": {}},
    })
    assert r.status_code == 200
    content = r.json()["result"]["content"]
    result = orjson.loads(content[0]["text"])
    assert "conversions" in result


# ─── A2A agent card ───────────────────────────────────────────────────────────

async def test_agent_card(client):
    r = await client.get("/.well-known/agent-card.json")
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "Transform Agent"
    assert data["payment"]["protocol"] == "x402"


async def test_mcp_manifest(client):
    r = await client.get("/.well-known/mcp.json")
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "Transform Agent"
    assert len(data["tools"]) == 9
