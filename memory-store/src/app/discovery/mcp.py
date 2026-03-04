"""
MCP Streamable HTTP handler — JSON-RPC 2.0 protocol.

Implements the Model Context Protocol over HTTP POST /mcp.
Methods: initialize, tools/list, tools/call
Six tools: memory_set, memory_get, memory_search, memory_list, memory_delete, memory_stats
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()

# ─── Tool Definitions ─────────────────────────────────────────────────────────

TOOLS = [
    {
        "name": "memory_set",
        "description": (
            "Store a value in persistent agent memory. "
            "Values survive session restarts and are accessible across agents. "
            "Optionally set a TTL for automatic expiry. "
            "Each stored value is also indexed for semantic search via memory_search. "
            "Price: $0.001/call (USDC on Base via x402)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "namespace": {
                    "type": "string",
                    "description": (
                        "Scoping prefix for this key. Use your agent's wallet address "
                        "for private storage (e.g. '0xAbCd...') or a logical name for "
                        "shared storage (e.g. 'shared/mcp-ecosystem-knowledge')."
                    ),
                },
                "key": {
                    "type": "string",
                    "description": (
                        "Unique key within the namespace. Path-style keys recommended "
                        "(e.g. 'research/topic/findings', 'session/2024-01/summary')."
                    ),
                },
                "value": {
                    "type": "string",
                    "description": (
                        "Value to store. Any string accepted; "
                        "JSON-serialized objects recommended for structured data. "
                        "Max 1MB per value."
                    ),
                },
                "ttl_seconds": {
                    "type": "integer",
                    "description": (
                        "Optional time-to-live in seconds. "
                        "Omit or set null for permanent storage."
                    ),
                },
            },
            "required": ["namespace", "key", "value"],
        },
    },
    {
        "name": "memory_get",
        "description": (
            "Retrieve a stored value by its exact key. "
            "Returns the value along with storage metadata (stored_at, expires_at). "
            "Returns found=false if the key does not exist or has expired. "
            "Price: $0.0001/call (USDC on Base via x402)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "namespace": {
                    "type": "string",
                    "description": "Namespace the key belongs to.",
                },
                "key": {
                    "type": "string",
                    "description": "Exact key to retrieve.",
                },
            },
            "required": ["namespace", "key"],
        },
    },
    {
        "name": "memory_search",
        "description": (
            "Semantic search over stored memory values using vector similarity. "
            "Embed your query and find the most relevant stored values — "
            "no need for exact key matches. "
            "Useful for recalling what an agent previously learned about a topic. "
            "Uses cosine similarity with all-MiniLM-L6-v2 embeddings (384 dims). "
            "Price: $0.01/call (USDC on Base via x402)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "namespace": {
                    "type": "string",
                    "description": "Namespace to search within.",
                },
                "query": {
                    "type": "string",
                    "description": (
                        "Natural language query. "
                        "Example: 'what did I learn about MCP adoption rates?'"
                    ),
                },
                "top_k": {
                    "type": "integer",
                    "description": "Maximum number of results to return. Range: 1-50. Default: 5.",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 50,
                },
                "min_score": {
                    "type": "number",
                    "description": (
                        "Minimum cosine similarity score (0.0-1.0). "
                        "Higher values return only high-confidence matches. "
                        "Default: 0.0 (return all results up to top_k)."
                    ),
                    "default": 0.0,
                    "minimum": 0.0,
                    "maximum": 1.0,
                },
            },
            "required": ["namespace", "query"],
        },
    },
    {
        "name": "memory_list",
        "description": (
            "List all keys stored in a namespace, with optional prefix filtering. "
            "Supports pagination via cursor for namespaces with many keys. "
            "Price: $0.0001/call (USDC on Base via x402)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "namespace": {
                    "type": "string",
                    "description": "Namespace to list keys from.",
                },
                "prefix": {
                    "type": "string",
                    "description": (
                        "Optional key prefix to filter results. "
                        "Example: 'research/' to list only research keys."
                    ),
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum keys to return per page. Range: 1-1000. Default: 100.",
                    "default": 100,
                    "minimum": 1,
                    "maximum": 1000,
                },
                "cursor": {
                    "type": "string",
                    "description": (
                        "Pagination cursor from the previous response's next_cursor field. "
                        "Omit for the first page."
                    ),
                },
            },
            "required": ["namespace"],
        },
    },
    {
        "name": "memory_delete",
        "description": (
            "Delete a key from persistent memory. "
            "Also removes the vector embedding for the key. "
            "Returns deleted=false if the key did not exist. "
            "Price: $0.0001/call (USDC on Base via x402)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "namespace": {
                    "type": "string",
                    "description": "Namespace the key belongs to.",
                },
                "key": {
                    "type": "string",
                    "description": "Key to delete.",
                },
            },
            "required": ["namespace", "key"],
        },
    },
    {
        "name": "memory_stats",
        "description": (
            "Get usage statistics and cost information for a namespace. "
            "Returns total keys, bytes stored, reads/writes today, and estimated cost. "
            "Price: FREE — no x402 payment required."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "namespace": {
                    "type": "string",
                    "description": "Namespace to retrieve statistics for.",
                },
            },
            "required": ["namespace"],
        },
    },
]

# ─── JSON-RPC Helpers ─────────────────────────────────────────────────────────


def _ok(id: str | int | None, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": id, "result": result}


def _err(id: str | int | None, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": id, "error": {"code": code, "message": message}}


# ─── Tool Dispatch ────────────────────────────────────────────────────────────


async def _call_tool(name: str, args: dict, request: Request) -> dict:
    redis_store = request.app.state.redis_store
    vector_store = request.app.state.vector_store

    if name == "memory_set":
        result = await redis_store.set(
            namespace=args["namespace"],
            key=args["key"],
            value=args["value"],
            ttl_seconds=args.get("ttl_seconds"),
        )
        try:
            await vector_store.store_embedding(
                namespace=args["namespace"],
                key=args["key"],
                value=args["value"],
                ttl_seconds=args.get("ttl_seconds"),
            )
        except Exception:
            pass
        return result

    elif name == "memory_get":
        return await redis_store.get(namespace=args["namespace"], key=args["key"])

    elif name == "memory_search":
        results = await vector_store.search(
            namespace=args["namespace"],
            query=args["query"],
            top_k=args.get("top_k", 5),
            min_score=args.get("min_score", 0.0),
        )
        return {
            "results": [r.model_dump() for r in results],
            "query": args["query"],
            "namespace": args["namespace"],
            "count": len(results),
        }

    elif name == "memory_list":
        return await redis_store.list(
            namespace=args["namespace"],
            prefix=args.get("prefix"),
            limit=args.get("limit", 100),
            cursor=args.get("cursor"),
        )

    elif name == "memory_delete":
        result = await redis_store.delete(namespace=args["namespace"], key=args["key"])
        try:
            await vector_store.delete_embedding(namespace=args["namespace"], key=args["key"])
        except Exception:
            pass
        return result

    elif name == "memory_stats":
        return await redis_store.stats(namespace=args["namespace"])

    else:
        raise ValueError(f"Unknown tool: {name}")


# ─── Route ────────────────────────────────────────────────────────────────────


@router.post("/mcp")
async def mcp_handler(request: Request) -> JSONResponse:
    """MCP Streamable HTTP endpoint — JSON-RPC 2.0."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(_err(None, -32700, "Parse error"), status_code=400)

    rpc_id = body.get("id")
    method = body.get("method")
    params = body.get("params", {})

    if body.get("jsonrpc") != "2.0":
        return JSONResponse(_err(rpc_id, -32600, "Invalid Request: jsonrpc must be '2.0'"))

    # ── initialize ──
    if method == "initialize":
        return JSONResponse(
            _ok(
                rpc_id,
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {
                        "name": "mcp-bank-memory-store",
                        "version": "1.0.0",
                    },
                },
            )
        )

    # ── tools/list ──
    elif method == "tools/list":
        return JSONResponse(_ok(rpc_id, {"tools": TOOLS}))

    # ── tools/call ──
    elif method == "tools/call":
        tool_name = params.get("name")
        tool_args = params.get("arguments", {})

        if not tool_name:
            return JSONResponse(_err(rpc_id, -32602, "Missing tool name"))

        try:
            result = await _call_tool(tool_name, tool_args, request)
        except ValueError as e:
            return JSONResponse(_err(rpc_id, -32601, str(e)))
        except Exception as e:
            return JSONResponse(
                _err(rpc_id, -32603, f"Internal error: {str(e)}"),
                status_code=500,
            )

        return JSONResponse(
            _ok(rpc_id, {"content": [{"type": "text", "text": str(result)}], "result": result})
        )

    else:
        return JSONResponse(_err(rpc_id, -32601, f"Method not found: {method}"))
