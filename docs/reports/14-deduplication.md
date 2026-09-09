# Rank 14 — Deduplication & Similarity: Completion Report

## Status: COMPLETE

## What Was Built
MCP deduplication and similarity service with 6 tools, dual dedup modes (exact hash + semantic embedding), fingerprinting (SHA-256, SimHash, MinHash), and x402 micropayment enforcement.

## Architecture
- **Runtime**: FastAPI + uvicorn
- **Embeddings**: sentence-transformers (`all-MiniLM-L6-v2`) for semantic similarity
- **Fingerprinting**: SHA-256 (exact), SimHash (near-duplicate), MinHash via datasketch (LSH-ready)
- **Cache**: Redis (optional, graceful degradation without it)
- **Payments**: x402 middleware (conditional on `WALLET_ADDRESS`)
- **Protocol**: MCP JSON-RPC 2024-11-05 via `POST /mcp`

## MCP Tools (6)
| Tool | Price | Mode |
|------|-------|------|
| `deduplicate` | $0.001/text | exact (threshold=1.0) or semantic |
| `similarity` | $0.0005 | semantic cosine similarity |
| `find_similar` | $0.001/candidate | semantic ranked search |
| `fingerprint` | $0.0002 | SHA-256 + SimHash + MinHash |
| `batch_fingerprint` | $0.00015/text | batch fingerprinting |
| `list_capabilities` | free | service info |

## Endpoints
- `GET /health` — health check (200)
- `POST /mcp` — MCP JSON-RPC
- `GET /.well-known/agent-card.json` — A2A agent card
- `GET /.well-known/mcp.json` — MCP discovery
- `GET /openapi.json` — OpenAPI schema
- `POST /api/deduplicate` — REST API
- `POST /api/similarity` — REST API
- `POST /api/find-similar` — REST API
- `POST /api/fingerprint` — REST API
- `POST /api/batch-fingerprint` — REST API

## Test Results
```
38 passed in 0.07s
```

### Test Coverage
- Health endpoint
- A2A agent card and MCP discovery
- OpenAPI schema
- MCP initialize + tools/list
- All 6 MCP tools (valid input, validation errors, edge cases)
- Engine unit tests (exact dedup, semantic dedup, similarity, find_similar)
- Fingerprint unit tests (determinism, all algorithms)
- Unknown method/tool error handling

## Acceptance Criteria Status

### Service-Level
- [x] Health endpoint returns 200 and stable JSON shape
- [x] `/.well-known/agent-card.json` exists with accurate capabilities
- [x] `POST /mcp` supports MCP JSON-RPC request/response flow
- [x] `/openapi.json` loads with no schema errors
- [x] x402 enforcement when `WALLET_ADDRESS` is set
- [x] Service starts without crash when Redis unavailable (degraded mode)
- [x] `uv run pytest -q` passes (38/38)
- [x] Dockerfile present and builds
- [x] Error responses are deterministic and machine-parseable

### Tool-Level
- [x] All 6 tools appear in MCP tool listing with correct names/descriptions
- [x] Valid inputs return expected output schemas
- [x] Invalid inputs return validation errors (not 500s)
- [x] Deterministic behavior for identical input (fingerprints, exact dedup)
- [x] Runtime and payload limits documented and enforced (max 10000 texts)
- [x] Response contracts align with SPEC

## Files Delivered
- `src/app/main.py` — FastAPI app factory
- `src/app/dependencies.py` — Redis DI
- `src/app/discovery/mcp.py` — MCP JSON-RPC handler
- `src/app/discovery/a2a.py` — Agent card + .well-known
- `src/app/dedup/engine.py` — Hash + semantic dedup engine
- `src/app/dedup/fingerprint.py` — SHA-256, SimHash, MinHash
- `src/app/models/schemas.py` — Pydantic v2 models
- `src/app/routes/health.py` — Health endpoint
- `src/app/routes/dedup.py` — REST API routes
- `tests/` — 5 test files, 38 tests
- `Dockerfile`, `fly.toml`, `pyproject.toml`, `README.md`, `.env.example`

## Risks / Open Items
- [NEEDS TESTING] Production performance under load with real embedding model
- [NEEDS TESTING] Redis caching of fingerprints (infrastructure-dependent)
- [UNVERIFIED] Revenue projections ($3-8k/month)
