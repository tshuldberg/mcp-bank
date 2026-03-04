# Memory Store

Hosted, persistent, cross-agent memory. MCP-native. x402-paid. No signup.

**Status:** In development — [see spec](./SPEC.md)

---

## The Problem

The local MCP memory server gets 67,000 downloads/week. It's ephemeral. It dies when your agent session ends. It can't share state between agents. There is no cloud version.

This is the cloud version.

---

## MCP Config

```json
{
  "mcpServers": {
    "mcp-bank-memory": {
      "url": "https://memory.mcp-bank.fly.dev/mcp"
    }
  }
}
```

---

## Tools

| Tool | Description | Price |
|------|-------------|-------|
| `memory_set` | Store any value, optionally with TTL | $0.001 |
| `memory_get` | Retrieve by exact key | $0.0001 |
| `memory_search` | Semantic search over stored values | $0.01 |
| `memory_list` | List keys in namespace | $0.0001 |
| `memory_delete` | Remove a key | $0.0001 |
| `memory_stats` | Usage and cost info | Free |

First 1,000 reads free per wallet.

---

## Quick Start (REST)

```bash
# Store something
curl -X POST https://memory.mcp-bank.fly.dev/memory/set \
  -H "Content-Type: application/json" \
  -H "X-Payment: <x402_payment_header>" \
  -d '{
    "namespace": "my-agent",
    "key": "research/mcp-ecosystem",
    "value": "{\"summary\": \"MCP has 11,415 servers as of 2025\"}"
  }'

# Retrieve it
curl -X POST https://memory.mcp-bank.fly.dev/memory/get \
  -H "Content-Type: application/json" \
  -H "X-Payment: <x402_payment_header>" \
  -d '{"namespace": "my-agent", "key": "research/mcp-ecosystem"}'

# Search semantically
curl -X POST https://memory.mcp-bank.fly.dev/memory/search \
  -H "Content-Type: application/json" \
  -H "X-Payment: <x402_payment_header>" \
  -d '{"namespace": "my-agent", "query": "MCP ecosystem size", "top_k": 5}'
```

---

## Payment

Uses [x402](https://x402.org) — automatic micropayments in USDC on Base. Your agent's CDP wallet handles it transparently.

```python
from x402.httpx import x402_client
from cdp import Wallet

wallet = Wallet.load("my-agent-wallet")

async with x402_client(wallet=wallet) as client:
    await client.post(
        "https://memory.mcp-bank.fly.dev/memory/set",
        json={"namespace": "my-agent", "key": "findings", "value": "..."}
    )
    # x402 handles the 402 → payment → retry automatically
```

---

## Discovery

- MCP: `https://memory.mcp-bank.fly.dev/mcp`
- A2A: `https://memory.mcp-bank.fly.dev/.well-known/agent-card.json`
- OpenAPI: `https://memory.mcp-bank.fly.dev/openapi.json`
