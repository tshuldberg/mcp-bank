"""
Encoding/decoding transforms: base64, hex, URL encoding.
"""

import base64
import urllib.parse


def to_base64(data: str) -> str:
    return base64.b64encode(data.encode()).decode()


def from_base64(data: str) -> str:
    return base64.b64decode(data).decode()


def to_hex(data: str) -> str:
    return data.encode().hex()


def from_hex(data: str) -> str:
    return bytes.fromhex(data).decode()


def to_url_encoded(data: str) -> str:
    return urllib.parse.quote(data, safe="")


def from_url_encoded(data: str) -> str:
    return urllib.parse.unquote(data)
