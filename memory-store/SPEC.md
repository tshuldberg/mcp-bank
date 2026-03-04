# Memory Store — Technical Spec

**Status:** In development
**Target deploy:** 2 weeks from spec approval

---

## What It Is

A hosted, persistent, cross-session, cross-agent key-value store with semantic vector search. MCP-native. Paid per operation via x402 (USDC on Base). No signup. No API keys. Agent identifies by wallet.

---

## Problem It Solves

Every production agent workflow needs persistent state:
- Research agents need to store what they found and recall it later
- Coding agents need to cache intermediate results across tool calls
- Orchestrator agents need to share state with sub-agents
- Any agent running across multiple sessions needs memory that survives restarts

Current solution: `@modelcontextprotocol/server-memory` — 67k downloads/week — is local-only, ephemeral, and dies on session restart. There is no cloud version.

---

## MCP Tools

### `memory_set`
Store a value in persistent memory.

```json
{
  "namespace": "agent-wallet-or-logical-name",
  "key": "research/topic/findings",
  "value": "{\"summary\": \"...\", \"sources\": [...]}",
  "ttl_seconds": null
}
```

Returns: `{"stored": true, "key": "...", "bytes": 1234}`

Price: **$0.001/call**

---

### `memory_get`
Retrieve a stored value by exact key.

```json
{
  "namespace": "agent-wallet-or-logical-name",
  "key": "research/topic/findings"
}
```

Returns: `{"value": "...", "stored_at": "...", "expires_at": null}`

Price: **$0.0001/call**

---

### `memory_search`
Semantic search over stored values using vector similarity.

```json
{
  "namespace": "agent-wallet-or-logical-name",
  "query": "what did I learn about MCP adoption rates?",
  "top_k": 5,
  "min_score": 0.7
}
```

Returns: array of `{"key": "...", "value": "...", "score": 0.94, "stored_at": "..."}`

Price: **$0.01/call**

---

### `memory_list`
Enumerate keys in a namespace.

```json
{
  "namespace": "agent-wallet-or-logical-name",
  "prefix": "research/",
  "limit": 100,
  "cursor": null
}
```

Returns: `{"keys": [...], "next_cursor": "...", "total": 347}`

Price: **$0.0001/call**

---

### `memory_delete`
Remove a key.

```json
{
  "namespace": "agent-wallet-or-logical-name",
  "key": "research/topic/findings"
}
```

Returns: `{"deleted": true}`

Price: **$0.0001/call**

---

### `memory_stats`
Usage and cost information for a namespace.

```json
{
  "namespace": "agent-wallet-or-logical-name"
}
```

Returns: `{"keys": 1247, "bytes": 4892341, "reads_today": 5023, "writes_today": 341, "cost_today_usd": 0.85}`

Price: **free**

---

## Namespacing

Namespaces are the scoping unit. An agent should use:
- Its wallet address for private state: `0xAbCd...`
- A logical name for shared/public state: `shared/mcp-ecosystem-knowledge`

Any agent can read from any namespace if it knows the name. Writes only allowed by the namespace owner (wallet that created it) — or to public namespaces.

**Private namespace:** Only the creating wallet can write. Anyone with the name can read.
**Public namespace:** Anyone can write. Useful for agent-to-agent data sharing.

Namespace privacy is set at creation and cannot be changed.

---

## Vector Search Architecture

1. On `memory_set`, the value is embedded using a local embedding model (sentence-transformers/all-MiniLM-L6-v2, runs on CPU, free)
2. Embedding stored in pgvector alongside the KV record
3. On `memory_search`, query is embedded and cosine similarity search runs over namespace

This means semantic search is included in the base price — no separate embedding API cost.

---

## Stack

```
FastAPI + uvicorn
Redis (KV operations, TTL support)
PostgreSQL + pgvector (vector search, metadata)
sentence-transformers (local embedding, no API cost)
x402 Python middleware
Fly.io (scale-to-zero)
```

---

## Pricing

| Operation | Price | Notes |
|-----------|-------|-------|
| `memory_set` | $0.001 | Per call regardless of value size |
| `memory_get` | $0.0001 | Per call |
| `memory_search` | $0.01 | Per query, top_k doesn't affect price |
| `memory_list` | $0.0001 | Per call |
| `memory_delete` | $0.0001 | Per call |
| `memory_stats` | Free | Always free |

First 1,000 reads (get + list) free per wallet address.

---

## Endpoints

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/memory/set` | Store value | x402 |
| POST | `/memory/get` | Retrieve value | x402 |
| POST | `/memory/search` | Semantic search | x402 |
| POST | `/memory/list` | List keys | x402 |
| POST | `/memory/delete` | Delete key | x402 |
| GET | `/memory/stats` | Usage info | x402 wallet |
| POST | `/mcp` | MCP Streamable HTTP | — |
| GET | `/.well-known/agent-card.json` | Google A2A | — |
| GET | `/openapi.json` | OpenAPI spec | — |
| GET | `/health` | Health check | — |

---

## Open Questions

- [ ] Storage limits per namespace? (start: 1GB soft limit, alert at 800MB)
- [ ] Value size limit? (start: 1MB per value)
- [ ] Cross-namespace reads: require payment? (lean: yes, same price as normal read)
- [ ] Embedding model: local vs. OpenAI? (lean: local, zero marginal cost)
- [ ] pgvector vs. dedicated vector DB (Qdrant)? (lean: pgvector, simpler ops)
