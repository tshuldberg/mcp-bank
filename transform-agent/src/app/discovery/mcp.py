"""
MCP Streamable HTTP handler for the Transform Agent.
POST /mcp — JSON-RPC 2.0 with 9 tools.
GET /.well-known/mcp.json — MCP manifest.
"""

import orjson
from fastapi import APIRouter, Request
from fastapi.responses import ORJSONResponse

from src.app.transforms import schema_ops
from src.app.transforms.registry import get_handler, list_capabilities
from src.app.middleware.cache import make_cache_key, cache_get, cache_set

router = APIRouter()

MCP_TOOLS = [
    {
        "name": "transform",
        "description": "Convert data from one format to another. Supports JSON, CSV, XML, YAML, TOML, HTML, Markdown, Text, PDF, XLSX, DOCX, Base64, Hex, URL encoding.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source_format": {"type": "string", "description": "Input format (json, csv, xml, yaml, toml, html, markdown, text, pdf, xlsx, docx, base64, hex, url)"},
                "target_format": {"type": "string", "description": "Output format"},
                "data": {"type": "string", "description": "Input data as string. Binary formats (pdf, xlsx, docx) must be base64-encoded."},
            },
            "required": ["source_format", "target_format", "data"],
        },
    },
    {
        "name": "validate",
        "description": "Validate JSON data against a JSON Schema. Returns a list of validation errors.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "data": {"type": "string", "description": "JSON data to validate"},
                "schema": {"type": "string", "description": "JSON Schema as a JSON string"},
                "data_format": {"type": "string", "default": "json"},
            },
            "required": ["data", "schema"],
        },
    },
    {
        "name": "infer_schema",
        "description": "Generate a JSON Schema from sample data. Useful for understanding the structure of unknown datasets.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "data": {"type": "string", "description": "Sample data (JSON array or object)"},
                "data_format": {"type": "string", "default": "json"},
                "strictness": {"type": "string", "enum": ["strict", "relaxed"], "default": "relaxed"},
            },
            "required": ["data"],
        },
    },
    {
        "name": "reshape",
        "description": "Restructure nested JSON using dot-notation path mapping. Extract deeply nested fields into a flat structure.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "data": {"description": "JSON data to reshape (object or array)"},
                "mapping": {
                    "type": "object",
                    "description": "Output field → dot-notation source path. E.g. {\"name\": \"user.profile.name\"}",
                    "additionalProperties": {"type": "string"},
                },
            },
            "required": ["data", "mapping"],
        },
    },
    {
        "name": "diff",
        "description": "Compare two JSON datasets and return added, removed, and modified records.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "before": {"type": "string", "description": "Original dataset (JSON array)"},
                "after": {"type": "string", "description": "Updated dataset (JSON array)"},
                "key_field": {"type": "string", "description": "Field to use as unique row identifier"},
                "data_format": {"type": "string", "default": "json"},
            },
            "required": ["before", "after", "key_field"],
        },
    },
    {
        "name": "merge",
        "description": "Join two tabular JSON datasets on a common key field.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "left": {"type": "string", "description": "Left dataset (JSON array)"},
                "right": {"type": "string", "description": "Right dataset (JSON array)"},
                "on": {"type": "string", "description": "Join key field name"},
                "how": {"type": "string", "enum": ["inner", "left", "right", "full"], "default": "inner"},
                "data_format": {"type": "string", "default": "json"},
            },
            "required": ["left", "right", "on"],
        },
    },
    {
        "name": "filter",
        "description": "Filter rows from a tabular JSON dataset using a simple expression (e.g. 'age >= 18', 'status == active').",
        "inputSchema": {
            "type": "object",
            "properties": {
                "data": {"type": "string", "description": "Tabular data (JSON array)"},
                "where": {"type": "string", "description": "Filter expression, e.g. 'age >= 18'"},
                "data_format": {"type": "string", "default": "json"},
            },
            "required": ["data", "where"],
        },
    },
    {
        "name": "sample",
        "description": "Randomly sample N rows from a tabular JSON dataset.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "data": {"type": "string", "description": "Tabular data (JSON array)"},
                "n": {"type": "integer", "default": 10, "minimum": 1, "maximum": 10000},
                "seed": {"type": "integer", "description": "Random seed for reproducibility"},
                "data_format": {"type": "string", "default": "json"},
            },
            "required": ["data"],
        },
    },
    {
        "name": "capabilities",
        "description": "List all supported format conversions and operations with pricing. Free — no payment required.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]


async def _handle_tool_call(name: str, args: dict) -> dict:
    """Dispatch a tool call and return the result dict."""
    if name == "transform":
        src, tgt = args["source_format"].lower(), args["target_format"].lower()
        data = args["data"]
        handler = get_handler(src, tgt)
        if handler is None:
            return {"error": f"Unsupported conversion: {src} → {tgt}", "code": "UNSUPPORTED_CONVERSION"}
        cache_key = make_cache_key(src, tgt, data)
        cached = await cache_get(cache_key)
        if cached:
            return {"result": cached, "source_format": src, "target_format": tgt, "cached": True}
        result = handler(data)
        await cache_set(cache_key, result)
        return {"result": result, "source_format": src, "target_format": tgt, "cached": False}

    elif name == "validate":
        return schema_ops.validate_data(args["data"], args["schema"])

    elif name == "infer_schema":
        return schema_ops.infer_schema(
            args["data"],
            args.get("data_format", "json"),
            args.get("strictness", "relaxed"),
        )

    elif name == "reshape":
        return schema_ops.reshape_json(args["data"], args["mapping"])

    elif name == "diff":
        return schema_ops.diff_data(args["before"], args["after"], args["key_field"])

    elif name == "merge":
        return schema_ops.merge_data(
            args["left"], args["right"], args["on"], args.get("how", "inner")
        )

    elif name == "filter":
        return schema_ops.filter_data(args["data"], args["where"])

    elif name == "sample":
        return schema_ops.sample_data(args["data"], args.get("n", 10), args.get("seed"))

    elif name == "capabilities":
        return {
            "conversions": list_capabilities(),
            "operations": {
                "validate": 0.0005,
                "infer_schema": 0.0005,
                "reshape": 0.002,
                "diff": 0.001,
                "merge": 0.001,
                "filter": 0.001,
                "sample": 0.0005,
            },
        }

    return {"error": f"Unknown tool: {name}", "code": "UNKNOWN_TOOL"}


@router.post("/mcp")
async def mcp_handler(request: Request) -> ORJSONResponse:
    """MCP Streamable HTTP — JSON-RPC 2.0 endpoint."""
    body = await request.json()

    rpc_id = body.get("id")
    method = body.get("method", "")
    params = body.get("params", {})

    def ok(result):
        return ORJSONResponse({"jsonrpc": "2.0", "id": rpc_id, "result": result})

    def err(code: int, message: str):
        return ORJSONResponse(
            {"jsonrpc": "2.0", "id": rpc_id, "error": {"code": code, "message": message}}
        )

    if method == "initialize":
        return ok({
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "transform-agent", "version": "1.0.0"},
        })

    elif method == "tools/list":
        return ok({"tools": MCP_TOOLS})

    elif method == "tools/call":
        tool_name = params.get("name")
        tool_args = params.get("arguments", {})
        if not tool_name:
            return err(-32602, "Missing tool name")
        try:
            result = await _handle_tool_call(tool_name, tool_args)
            return ok({"content": [{"type": "text", "text": orjson.dumps(result).decode()}]})
        except Exception as e:
            return err(-32603, str(e))

    else:
        return err(-32601, f"Method not found: {method}")


@router.get("/.well-known/mcp.json")
async def mcp_manifest() -> ORJSONResponse:
    import os
    base_url = os.environ.get("BASE_URL", "https://mcp-bank-transform.fly.dev")
    return ORJSONResponse({
        "schema_version": "1.0",
        "name": "Transform Agent",
        "description": "Data format conversion and validation. 20+ format pairs, x402-paid.",
        "mcp_endpoint": f"{base_url}/mcp",
        "tools": [{"name": t["name"], "description": t["description"]} for t in MCP_TOOLS],
    })
