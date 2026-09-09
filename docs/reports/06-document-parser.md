# Rank 6: Document Parser

## Completion Status

Rank 6 document parser has been implemented in production-ready form in `/Volumes/2TB/Apps/mcp-document-parser` with MCP + A2A discovery + x402 wallet-gating behavior.

## Feature Set Delivered

- FastAPI runtime with structured schemas for PDF/DOCX/XLSX parse results.
- Core parse endpoints:
  - `POST /parse/pdf`
  - `POST /parse/docx`
  - `POST /parse/xlsx`
  - `POST /parse/url`
  - `POST /parse/tables`
- Required public protocol endpoints:
  - `POST /mcp`
  - `GET /.well-known/agent-card.json`
  - `GET /openapi.json`
- MCP JSON-RPC tool surface with protocol target `2024-11-05`:
  - `initialize`
  - `tools/list`
  - `tools/call`
- A2A discovery artifacts:
  - `/.well-known/agent-card.json`
  - `/.well-known/mcp.json`
- Redis-backed caching with 1-hour TTL and model-safe cache deserialization.
- x402 wallet-gated middleware wiring:
  - Uses official middleware when available.
  - Falls back to local 402-compatible middleware if official import path/deps are unavailable.
  - Enforces `WALLET_ADDRESS` requirement when `ENVIRONMENT=production`.
- Deployment/project artifacts completed:
  - `README.md`
  - `Dockerfile`
  - `fly.toml`
  - `.env.example`
  - `pyproject.toml`

## Profitability Thesis

- Pricing map implemented per SPEC:
  - `parse_pdf`: $0.008
  - `parse_docx`: $0.005
  - `parse_xlsx`: $0.005
  - `parse_from_url`: $0.010
  - `extract_tables`: $0.006
- Cached result policy: 50% price equivalent (billing/accounting integration external) [UNVERIFIED].
- Revenue expectation at scale (10k agent customers) remains directional from rank thesis and depends on paid-call conversion and retention [UNVERIFIED].

## KPI Tracking Plan

Track weekly and monthly:

- Paid calls/day by tool and by unique agent.
- Revenue/day and ARPA [UNVERIFIED until live billing feed is connected].
- Cache hit rate and implied gross margin lift [UNVERIFIED].
- p50/p95 latency and endpoint-level error rates.
- Retry rate and payment-failure rate.
- 7-day and 30-day retention for paying agents.

## Validation Notes

- Parser test suite run (offline shim): `8 passed, 0 failed`.
- Required protocol endpoints confirmed present.
- MCP initialize advertises protocol version `2024-11-05`.
- Full required command `uv sync && uv run pytest -q` could not complete in this environment due disabled network and uncached package resolution [NEEDS TESTING].

## Risks

- Real x402 facilitator/payment interoperability needs live end-to-end verification [NEEDS TESTING].
- Load behavior and memory profile for large binary documents not yet performance-tested [NEEDS TESTING].
- URL-fetch parser may face untrusted-file edge cases and malicious payload patterns [NEEDS TESTING].
- Profitability assumptions rely on demand and conversion not yet observed in production [UNVERIFIED].
