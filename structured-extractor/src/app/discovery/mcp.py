"""
MCP Streamable HTTP handler for the Structured Extractor.
POST /mcp — JSON-RPC 2.0 with 5 tools.
GET /.well-known/mcp.json — MCP manifest.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import orjson
from fastapi import APIRouter, Request
from fastapi.responses import ORJSONResponse

from src.app.extraction import pipeline

router = APIRouter()

MCP_TOOLS = [
    {
        "name": "extract",
        "description": (
            "Extract structured data from a URL matching a JSON Schema. "
            "Uses fast CSS/heuristic extraction first (JSON-LD, OpenGraph, microdata, CSS patterns). "
            "Falls back to Claude Haiku LLM extraction if confidence is below 0.8. "
            "Price: $0.005/request (HTML-only). Cached results: $0.0025."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to fetch and extract data from.",
                },
                "schema": {
                    "type": "object",
                    "description": (
                        "JSON Schema describing the structure you want to extract. "
                        "Example: {\"type\": \"object\", \"properties\": {\"name\": {\"type\": \"string\"}, "
                        "\"price\": {\"type\": \"number\"}}, \"required\": [\"name\", \"price\"]}"
                    ),
                },
                "render_js": {
                    "type": "boolean",
                    "default": False,
                    "description": "Render JavaScript before extraction. Not yet available (planned).",
                },
            },
            "required": ["url", "schema"],
        },
    },
    {
        "name": "extract_from_html",
        "description": (
            "Extract structured data from raw HTML matching a JSON Schema. "
            "Use this when you already have the HTML content — no URL fetch required. "
            "Price: $0.003/request."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "html": {
                    "type": "string",
                    "description": "Raw HTML string to extract data from.",
                },
                "schema": {
                    "type": "object",
                    "description": "JSON Schema describing the fields to extract.",
                },
            },
            "required": ["html", "schema"],
        },
    },
    {
        "name": "extract_from_image",
        "description": (
            "Extract structured data from an image URL using Claude Haiku vision. "
            "Useful for screenshots, product photos, scanned documents, etc. "
            "Price: $0.020/request. Maximum image size: 10MB."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "image_url": {
                    "type": "string",
                    "description": "URL of the image to analyze (max 10MB).",
                },
                "schema": {
                    "type": "object",
                    "description": "JSON Schema describing the fields to extract from the image.",
                },
            },
            "required": ["image_url", "schema"],
        },
    },
    {
        "name": "extract_batch",
        "description": (
            "Extract structured data from multiple URLs using the same JSON Schema. "
            "Processes URLs concurrently (configurable). "
            "Price: $0.004/URL (batch discount vs $0.005 single). Maximum 50 URLs per request."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "urls": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of URLs to extract from (max 50).",
                    "maxItems": 50,
                },
                "schema": {
                    "type": "object",
                    "description": "JSON Schema applied to all URLs.",
                },
                "render_js": {
                    "type": "boolean",
                    "default": False,
                    "description": "JS rendering for all URLs. Not yet available.",
                },
                "max_concurrent": {
                    "type": "integer",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 20,
                    "description": "Maximum concurrent extractions.",
                },
            },
            "required": ["urls", "schema"],
        },
    },
    {
        "name": "list_capabilities",
        "description": (
            "List all supported extraction types, pricing, confidence scoring details, "
            "and rate limits. Always free — no payment required."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]


async def _handle_tool(name: str, args: dict) -> dict:
    """Dispatch MCP tool calls to pipeline functions."""
    if name == "extract":
        result = await pipeline.extract(
            url=args["url"],
            schema=args["schema"],
            render_js=args.get("render_js", False),
        )
        return result.model_dump()

    elif name == "extract_from_html":
        result = await pipeline.extract_from_html(
            html=args["html"],
            schema=args["schema"],
        )
        return result.model_dump()

    elif name == "extract_from_image":
        result = await pipeline.extract_from_image(
            image_url=args["image_url"],
            schema=args["schema"],
        )
        return result.model_dump()

    elif name == "extract_batch":
        result = await pipeline.extract_batch(
            urls=args["urls"],
            schema=args["schema"],
            render_js=args.get("render_js", False),
            max_concurrent=args.get("max_concurrent", 5),
        )
        return result.model_dump()

    elif name == "list_capabilities":
        return {
            "extraction_types": {
                "extract": {"price_usd": 0.005},
                "extract_html": {"price_usd": 0.003},
                "extract_image": {"price_usd": 0.020},
                "extract_batch": {"price_usd_per_url": 0.004, "max_urls": 50},
            },
            "extraction_methods": ["json_ld", "opengraph", "microdata", "css_heuristic", "llm_haiku", "vision_llm"],
        }

    return {"error": f"Unknown tool: {name}", "code": "UNKNOWN_TOOL"}


@router.post("/mcp")
async def mcp_handler(request: Request) -> ORJSONResponse:
    """MCP Streamable HTTP — JSON-RPC 2.0 endpoint."""
    body = await request.json()

    rpc_id = body.get("id")
    method = body.get("method", "")
    params = body.get("params", {})

    def ok(result: dict) -> ORJSONResponse:
        return ORJSONResponse({"jsonrpc": "2.0", "id": rpc_id, "result": result})

    def err(code: int, message: str) -> ORJSONResponse:
        return ORJSONResponse(
            {"jsonrpc": "2.0", "id": rpc_id, "error": {"code": code, "message": message}}
        )

    if method == "initialize":
        return ok({
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "structured-extractor", "version": "1.0.0"},
        })

    elif method == "tools/list":
        return ok({"tools": MCP_TOOLS})

    elif method == "tools/call":
        tool_name = params.get("name")
        tool_args = params.get("arguments", {})
        if not tool_name:
            return err(-32602, "Missing tool name")
        try:
            result = await _handle_tool(tool_name, tool_args)
            return ok({"content": [{"type": "text", "text": orjson.dumps(result).decode()}]})
        except NotImplementedError as e:
            return err(-32603, str(e))
        except Exception as e:
            return err(-32603, str(e))

    else:
        return err(-32601, f"Method not found: {method}")


@router.get("/.well-known/mcp.json")
async def mcp_manifest() -> ORJSONResponse:
    base_url = os.environ.get("BASE_URL", "https://mcp-bank-extractor.fly.dev")
    return ORJSONResponse({
        "schema_version": "1.0",
        "name": "Structured Extractor",
        "description": (
            "Extract structured JSON from any URL, HTML, or image using a JSON Schema. "
            "CSS/heuristic first, LLM fallback. x402-paid via USDC on Base."
        ),
        "mcp_endpoint": f"{base_url}/mcp",
        "tools": [{"name": t["name"], "description": t["description"]} for t in MCP_TOOLS],
    })
