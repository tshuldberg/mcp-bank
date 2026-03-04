# AGENTS.md — mcp-bank

Instructions for AI coding agents (Claude Code, Codex, Cursor, etc.) working in this repo.

---

## Project Overview

mcp-bank is a suite of infrastructure primitives for the agent-to-agent economy.

- **Memory Store** (`memory-store/`) — hosted persistent agent memory, x402-paid
- **Transform Agent** (`transform-agent/`) — data format conversion + validation, x402-paid
- **Code Executor** (`code-executor/`) — sandboxed code execution, x402-paid (planned)

All services: FastAPI + Python 3.12 + x402 + Fly.io.

---

## Development Rules

### Python Style
- Python 3.12+. Use `X | Y` union types, not `Optional[X]`.
- Pydantic v2 everywhere. No raw dicts for request/response models.
- `orjson` for serialization (not stdlib json). `orjson.dumps(x).decode()` for strings.
- Async all the way down. No sync IO in request handlers.
- Type hints on every function signature.

### Structure
- Routes go in `src/app/routes/`
- Business logic goes in `src/app/[domain]/`
- No business logic in route handlers — handlers call service functions only
- Keep shared utilities in `shared/` at repo root

### x402 Payments
- Never bypass x402 middleware for any billable endpoint
- Always call `extract_agent_wallet()` for per-agent tracking
- Free operations: health checks, capability lists, stats endpoints
- Check `shared/x402_middleware.py` for standard patterns

### Testing
- Test files in `tests/` alongside `src/`
- Use `pytest` + `httpx.AsyncClient` for route testing
- Mock x402 verification in tests (don't make real payments in CI)
- Minimum: one test per MCP tool, one test for payment rejection on unpaid endpoints

### MCP Tools
- All tools must have complete docstrings (used as MCP tool descriptions)
- Tool parameters must be typed with Pydantic models, not raw dicts
- Return structured dicts, never raw strings
- Error responses: `{"error": "message", "code": "ERROR_CODE"}`

---

## Running Locally

```bash
cd memory-store  # or transform-agent
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env  # fill in WALLET_ADDRESS, etc.
uvicorn src.app.main:app --reload --port 8080
```

---

## Deployment

```bash
fly deploy  # from service directory
```

Secrets are set via `fly secrets set KEY=value`. Never commit `.env` files.

---

## Key Files

| File | Purpose |
|------|---------|
| `shared/x402_middleware.py` | x402 payment setup + agent wallet extraction |
| `shared/a2a_card.py` | Google A2A agent card generator |
| `docs/ARCHITECTURE.md` | Full stack + deployment patterns |
| `docs/ROADMAP.md` | Build order and milestones |
| `memory-store/SPEC.md` | Memory Store API spec |
| `transform-agent/SPEC.md` | Transform Agent API spec |

---

## Do Not

- Do not add user authentication (no accounts — wallet identity only)
- Do not add free tiers without Trey's approval (pricing is intentional)
- Do not store raw payment data in logs (wallet addresses in logs are fine, amounts are fine, but not full payment payloads)
- Do not add external API dependencies without documenting the cost model
