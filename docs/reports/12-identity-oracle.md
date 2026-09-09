# Rank 12 — Identity Oracle: Completion Report

## Summary
Wallet-based agent identity registry with reputation scoring. Agents register metadata, build reputation via interactions, and query trustworthiness of other agents.

## Deliverables

### Core Service
- **main.py** — FastAPI app with MCP endpoint, A2A card, x402 enforcement
- **identity/store.py** — In-memory store for profiles and interactions
- **identity/reputation.py** — Reputation scoring: `score = (success_rate × 0.5) + (log(n+1)/10 × 0.3) + (verified × 0.2)`
- **models/schemas.py** — Pydantic request/response schemas

### Protocol
- **discovery/mcp.py** — MCP JSON-RPC handler (protocol 2024-11-05), 7 tools
- **discovery/a2a.py** — Agent card at `/.well-known/agent-card.json`
- **routes/health.py** — Health check endpoint
- **routes/identity.py** — REST API (register, profile, interaction, reputation, search, capabilities)

### MCP Tools (7)
| Tool | Price | Status |
|------|-------|--------|
| `register` | $0.01 | PASS |
| `get_profile` | $0.001 | PASS |
| `record_interaction` | $0.002 | PASS |
| `get_reputation` | $0.002 | PASS |
| `search_agents` | $0.005 | PASS |
| `verify_wallet` | $0.003 | PASS |
| `list_capabilities` | free | PASS |

### Tests
- **43 tests passing** across 4 test files
- `test_store.py` — Store CRUD, search, verification (9 tests)
- `test_reputation.py` — Scoring algorithm, edge cases (8 tests)
- `test_mcp.py` — All 7 MCP tools + protocol methods (15 tests)
- `test_routes.py` — HTTP endpoints, REST API, health, A2A (11 tests)

### Deployment
- **Dockerfile** — Python 3.12 slim, uv-based
- **fly.toml** — Fly.io config, shared CPU, 256MB, ord region
- **.gitignore** — Standard Python ignores

## Quality Gates
- [x] `uv sync` succeeds
- [x] `uv run pytest -q` — 43 passed
- [x] OpenAPI schema generated and valid
- [x] Health endpoint returns 200
- [x] MCP initialize/tools/list/tools/call work
- [x] A2A agent card served
- [x] x402 enforcement gated on WALLET_ADDRESS env var
- [x] No secrets in repo

## Architecture
```
src/app/
├── main.py              # FastAPI app + x402 middleware
├── models/schemas.py    # Pydantic models
├── identity/
│   ├── store.py         # In-memory profile/interaction store
│   └── reputation.py    # Scoring algorithm
├── discovery/
│   ├── mcp.py           # MCP JSON-RPC handler
│   └── a2a.py           # Agent card
└── routes/
    ├── health.py        # GET /health
    └── identity.py      # REST API /api/v1/*
```

## Notes
- In-memory store used for v1; PostgreSQL + Redis ready to swap in
- Wallet verification is stubbed (would call Base RPC in production)
- Interaction decay not yet implemented (spec mentions slow decay)
