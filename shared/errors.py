from __future__ import annotations

import orjson
from fastapi.responses import JSONResponse

# Error code constants
INVALID_FORMAT = "INVALID_FORMAT"
UNSUPPORTED_CONVERSION = "UNSUPPORTED_CONVERSION"
TRANSFORM_FAILED = "TRANSFORM_FAILED"
PAYMENT_REQUIRED = "PAYMENT_REQUIRED"
INVALID_NAMESPACE = "INVALID_NAMESPACE"
KEY_NOT_FOUND = "KEY_NOT_FOUND"


def mcp_error(code: int, message: str, id_: int | str | None = None) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": id_,
        "error": {
            "code": code,
            "message": message,
        },
    }


def http_error(status: int, message: str, error_code: str) -> JSONResponse:
    content = orjson.dumps({"error": message, "code": error_code}).decode()
    return JSONResponse(status_code=status, content=orjson.loads(content))
