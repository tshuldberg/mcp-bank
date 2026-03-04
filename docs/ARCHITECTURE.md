# Architecture — Shared Patterns

All mcp-bank services follow the same structural pattern. This document captures it once.

---

## Stack

```
FastAPI (Python 3.12)
├── orjson           — fast JSON serialization
├── uvicorn          — ASGI server
├── pydantic v2      — request/response models
└── httpx            — async HTTP client

Payment
└── x402            — Coinbase CDP middleware (pip install x402)

Storage (Memory Store only)
├── Redis            — KV operations
└── pgvector         — vector search (via asyncpg)

Deployment
└── Fly.io           — scale-to-zero, global edge
```

---

## Project Layout

```
service-name/
├── src/
│   └── app/
│       ├── main.py              # FastAPI app + route registration
│       ├── models/
│       │   └── schemas.py       # Pydantic models
│       ├── routes/
│       │   ├── health.py        # GET /health
│       │   └── [domain].py      # Core service routes
│       ├── discovery/
│       │   ├── mcp.py           # MCP Streamable HTTP handler
│       │   ├── a2a_card.py      # Google A2A agent card
│       │   └── openapi.py       # OpenAPI customization
│       ├── payment/
│       │   └── x402.py          # x402 middleware config + pricing
│       ├── auth/
│       │   └── provision.py     # Wallet-based agent identity
│       └── middleware/
│           ├── metering.py      # Usage tracking + revenue logging
│           └── rate_limit.py    # Sliding-window rate limiter
├── tests/
│   └── test_*.py
├── Dockerfile
├── fly.toml
├── pyproject.toml
├── .env.example
└── README.md
```

---

## Discovery Endpoints (Every Service)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/mcp` | MCP Streamable HTTP (JSON-RPC 2.0) |
| GET | `/.well-known/agent-card.json` | Google A2A agent card |
| GET | `/.well-known/mcp.json` | MCP manifest |
| GET | `/openapi.json` | OpenAPI spec |
| POST | `/auth/provision` | Wallet-based identity (no signup) |

---

## Payment Flow (x402)

```python
# server-side (one middleware call)
from x402.fastapi import x402_middleware

app.add_middleware(
    x402_middleware,
    wallet_address=os.environ["WALLET_ADDRESS"],
    pricing={
        "POST /memory/set":    {"amount": "0.001",  "currency": "USDC", "network": "base"},
        "POST /memory/get":    {"amount": "0.0001", "currency": "USDC", "network": "base"},
        "POST /memory/search": {"amount": "0.01",   "currency": "USDC", "network": "base"},
    }
)
```

```python
# client-side (one function call)
from x402.httpx import x402_client

async with x402_client(wallet=agent_wallet) as client:
    resp = await client.post("https://memory.mcp-bank.fly.dev/memory/set", json={...})
```

---

## Agent Identity

Rather than API keys, agents identify by their CDP wallet address. This enables:
- Per-agent usage tracking
- Volume discounts (future)
- Reputation scoring (future)
- Cross-service identity (same wallet = same agent across Memory Store + Transform)

```python
# Verify agent identity from x402 payment header
agent_wallet = extract_wallet_from_x402_header(request)
```

---

## MCP Tool Schema Pattern

```python
@mcp_server.tool()
async def memory_set(
    namespace: str,
    key: str,
    value: str,
    ttl_seconds: int | None = None
) -> dict:
    """
    Store a value in persistent agent memory.

    Args:
        namespace: Scoping prefix. Use your agent's wallet address or a logical name.
        key: Unique key within the namespace.
        value: Any string value (JSON-serialized recommended for structured data).
        ttl_seconds: Optional expiry. Omit for permanent storage.

    Returns:
        {"stored": true, "key": "...", "namespace": "...", "expires_at": ...}
    """
```

---

## Deployment (Fly.io)

```toml
# fly.toml — common config
[build]
  dockerfile = "Dockerfile"

[env]
  PORT = "8080"
  ENVIRONMENT = "production"

[[services]]
  internal_port = 8080
  protocol = "tcp"

  [[services.ports]]
    handlers = ["tls", "http"]
    port = 443

  [services.concurrency]
    type = "requests"
    hard_limit = 500
    soft_limit = 400

# Scale to zero — costs nothing when idle
[services.auto_stop_machines]
  enabled = true
  min_machines_running = 0
```

```bash
# Deploy
fly launch --copy-config
fly secrets set WALLET_ADDRESS=0x... ADMIN_KEY=...
fly deploy
```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `WALLET_ADDRESS` | Yes | USDC destination on Base |
| `CDP_API_KEY_ID` | Yes | Coinbase CDP key for x402 facilitation |
| `CDP_API_KEY_SECRET` | Yes | Coinbase CDP secret |
| `ADMIN_KEY` | Yes | Internal admin operations |
| `REDIS_URL` | Memory Store only | Redis connection string |
| `DATABASE_URL` | Memory Store only | pgvector connection string |
| `ENVIRONMENT` | No | `development` or `production` |
