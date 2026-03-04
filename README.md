# mcp-bank

A suite of infrastructure primitives for the agent-to-agent economy.

MCP-native. x402-paid. No signup. No UI. Machine serves machine.

---

## Thesis

Millions of specialized agents will offer micro-services to each other. The agent that stores memory. The agent that converts formats. The agent that runs code in a sandbox. Each is simple, fast, and cheap. The money is in volume.

We're building the banking layer — the foundational infrastructure primitives every agent needs constantly.

---

## Products

### 1. Memory Store (active)

Hosted, persistent, cross-session, cross-agent memory with semantic search.

The local MCP memory server gets 67k downloads/week. There is no cloud version. We're building it.

- KV storage: `$0.0001/read`, `$0.001/write`
- Vector search: `$0.01/query`
- First 1,000 reads free per wallet
- MCP + OpenAPI + Google A2A discovery

→ [memory-store/](./memory-store/)

### 2. Transform Agent (active)

Stateless data format conversion: 43+ format pairs. JSON, CSV, XML, YAML, TOML, HTML, Markdown, PDF, Excel, DOCX, and more. Schema validation, inference, diff, merge, filter.

- Text transforms: `$0.001`
- Document transforms: `$0.005`
- Validation/schema: `$0.0005`

→ [transform-agent/](./transform-agent/)

### 3. Code Executor (planned)

Sandboxed Python/JS/Bash execution. Agents generate code constantly and need a safe place to run it. E2B charges $0.10+/hr and requires signup. We charge `$0.001/10-second slot` with x402 and no account.

→ [code-executor/](./code-executor/)

---

## Discovery

All services are listed on:
- [Smithery](https://smithery.ai/)
- [mcp.so](https://mcp.so/)
- Anthropic's remote MCP server directory

All expose:
- MCP (Streamable HTTP) at `/mcp`
- Google A2A agent card at `/.well-known/agent-card.json`
- OpenAPI spec at `/openapi.json`

---

## Payment

All services use [x402](https://www.x402.org/) — the HTTP-native micropayment protocol built on USDC/Base.

```
Agent sends request
  → Server returns HTTP 402 with payment requirements
  → Agent wallet signs and sends USDC
  → Server verifies on-chain
  → Service rendered
  → USDC lands in wallet
```

No Stripe. No invoices. No forms. Machine pays machine.

---

## Stack

- **Runtime:** FastAPI + Python 3.12
- **Performance:** orjson, polars, uvicorn
- **Payments:** x402 (Coinbase CDP)
- **Deployment:** Fly.io (scale-to-zero)
- **Memory:** Redis (KV) + pgvector (semantic search)
- **Discovery:** MCP Streamable HTTP, Google A2A, OpenAPI

---

## Docs

- [Market Analysis](./docs/ANALYSIS.md) — Research on agent needs and MCP ecosystem gaps
- [Roadmap](./docs/ROADMAP.md) — Build order and milestones
- [Opportunity](./docs/OPPORTUNITY.md) — The agent economy thesis in full
- [Architecture](./docs/ARCHITECTURE.md) — Shared patterns across all services

---

## Status

| Service | Status | Endpoint |
|---------|--------|----------|
| Memory Store | In development | — |
| Transform Agent | In development | — |
| Code Executor | Planned | — |

---

## Local Development

```bash
# Start all services (Redis, Postgres/pgvector, memory-store, transform-agent)
make dev

# Run all tests
make test

# Run tests for a single service
make test-memory
make test-transform

# Lint all services
make lint

# Tear down
make dev-down
```

Copy `.env.example` to `.env` and fill in your CDP wallet credentials before starting.

---

## Architecture

```
                        ┌─────────────────────────────────────────┐
                        │              Agent (client)              │
                        └──────────────┬──────────────────────────┘
                                       │ HTTP + x402 micropayment
                    ┌──────────────────┼──────────────────────┐
                    │                  │                       │
                    ▼                  ▼                       ▼
          ┌─────────────────┐ ┌─────────────────┐   future services...
          │  Memory Store   │ │ Transform Agent │
          │  :8080 / Fly.io │ │  :8081 / Fly.io │
          └────────┬────────┘ └────────┬────────┘
                   │                   │
          ┌────────▼────────┐ ┌────────▼────────┐
          │  pgvector        │ │     Redis       │
          │  (vector search) │ │  (rate limits / │
          │  + Redis (KV)    │ │   cache)        │
          └─────────────────┘ └─────────────────┘

x402 Payment Flow:
  Agent → POST /memory/set
        ← 402 Payment Required (USDC/Base, $0.001)
  Agent → POST /memory/set + X-PAYMENT header (signed USDC tx)
        ← 200 OK + result
        ← USDC settles to WALLET_ADDRESS on Base
```

Deploy a single service or all at once:

```bash
make deploy-memory    # fly deploy from memory-store/
make deploy-transform # fly deploy from transform-agent/
make deploy           # both
```
