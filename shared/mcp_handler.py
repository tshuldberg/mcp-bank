from __future__ import annotations

from shared.errors import mcp_error


class MCPHandler:
    server_name: str  # override in subclass
    server_version: str = "1.0.0"

    async def get_tools(self) -> list[dict]:
        raise NotImplementedError

    async def call_tool(self, name: str, arguments: dict) -> dict:
        raise NotImplementedError

    async def handle_request(self, body: dict) -> dict:
        method = body.get("method")
        id_ = body.get("id")

        if method == "initialize":
            return self._initialize(id_)
        if method == "tools/list":
            return await self._tools_list(id_)
        if method == "tools/call":
            return await self._tools_call(body.get("params", {}), id_)

        return mcp_error(-32601, "Method not found", id_)

    def _initialize(self, id_: int | str | None) -> dict:
        return {
            "jsonrpc": "2.0",
            "id": id_,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {
                    "name": self.server_name,
                    "version": self.server_version,
                },
            },
        }

    async def _tools_list(self, id_: int | str | None) -> dict:
        tools = await self.get_tools()
        return {
            "jsonrpc": "2.0",
            "id": id_,
            "result": {"tools": tools},
        }

    async def _tools_call(self, params: dict, id_: int | str | None) -> dict:
        name = params.get("name")
        arguments = params.get("arguments", {})

        if not name:
            return mcp_error(-32602, "Missing tool name", id_)

        result = await self.call_tool(name, arguments)
        return {
            "jsonrpc": "2.0",
            "id": id_,
            "result": {"content": [{"type": "text", "text": str(result)}]},
        }
