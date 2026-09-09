# Rank 11: Job Scheduler — Build Report

## Summary
Complete implementation of the MCP Job Scheduler service. Agents can schedule future HTTP callbacks (one-shot or cron) and the service delivers them with 3x retry on failure.

## Deliverables

### Source Files
- **src/app/main.py** — FastAPI app with CORS, lifespan (scheduler init), memory/PostgreSQL store selection
- **src/app/discovery/mcp.py** — MCP JSON-RPC endpoint (protocol 2024-11-05), all 8 tools
- **src/app/discovery/a2a.py** — A2A agent card + mcp.json manifest
- **src/app/scheduler/engine.py** — APScheduler + croniter for cron parsing, httpx callback delivery with 3x retry
- **src/app/scheduler/store.py** — PostgreSQL job store (asyncpg)
- **src/app/scheduler/memory_store.py** — In-memory store for tests (same interface)
- **src/app/models/schemas.py** — Pydantic models: Job, JobStatus, JobType, request schemas
- **src/app/routes/health.py** — Health check endpoint
- **src/app/routes/scheduler.py** — REST API for all scheduler operations

### 8 MCP Tools
| Tool | Description | Price |
|------|-------------|-------|
| schedule_once | One-time HTTP callback | $0.005 |
| schedule_cron | Recurring cron callback | $0.010 |
| cancel | Cancel a job | $0.001 |
| get_job | Get job details | $0.0001 |
| list_jobs | List jobs (optional status filter) | $0.001 |
| pause | Pause a job | $0.001 |
| resume | Resume a paused job | $0.001 |
| list_capabilities | Service info | free |

### Tests — 32 passing
- **test_mcp_tools.py** (13) — All 8 MCP tools via JSON-RPC, invalid cron, not-found, status filter, unknown method
- **test_engine.py** (8) — One-shot, cron scheduling, callback success, retry-then-fail, cron stays pending, cancel, pause/resume, wrong owner
- **test_rest.py** (8) — REST API for schedule/cancel/pause/resume/get/list
- **test_discovery.py** (2) — A2A card, MCP manifest
- **test_health.py** (1) — Health check

### Deployment
- **Dockerfile** — Python 3.12 slim, uvicorn
- **fly.toml** — Fly.io config, ord region, auto-stop
- **pyproject.toml** — All deps: fastapi, uvicorn, httpx, croniter, apscheduler, asyncpg, pydantic, orjson, x402

## Architecture
```
POST /mcp (JSON-RPC) → MCP router → SchedulerEngine → MemoryJobStore/JobStore
                                          ↓
                                    httpx callback delivery (3x retry)
```

## Key Decisions
- APScheduler v3 (v4 not yet released) — used primarily for background scheduling; croniter handles cron expression validation and next-run computation
- In-memory store mirrors PostgreSQL store interface exactly, enabling full test coverage without a database
- Callback retry: 3 attempts with 1s/2s/4s delays, then mark failed
- Owner wallet passed via `x-owner-wallet` header for ownership-scoped operations
