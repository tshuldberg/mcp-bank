# Market Analysis — Agent Economy Infrastructure

*Research conducted: 2026-03-03*

---

## Signal: What Agents Actually Download

Source: Glama "State of MCP in 2025" — NPM download data for MCP packages.

| Package | Downloads/week | What it tells us |
|---------|---------------|-----------------|
| `@playwright/mcp` | 951,444 | Browser automation is #1 need |
| `@upstash/context7-mcp` | 396,605 | Docs/knowledge access is #2 |
| `@modelcontextprotocol/server-filesystem` | 197,481 | File I/O is fundamental |
| `chrome-devtools-mcp` | 124,998 | More browser |
| `@modelcontextprotocol/server-memory` | **66,986** | **Persistent memory — LOCAL ONLY** |
| `@modelcontextprotocol/server-sequential-thinking` | 82,078 | Reasoning support |

**The memory insight:** 67k downloads/week on a local-only, ephemeral, stdio-only memory server. Zero cloud version. Zero x402 version. Zero cross-agent sharing. This is the gap.

---

## MCP Ecosystem State

- 11,415 MCP servers registered in 2025
- 31M weekly NPM downloads across ecosystem
- ~half of MCP companies that launched in 2025 have since died or pivoted
- Remote servers won overwhelmingly — users don't want to run local binaries

**Saturated categories (30+ servers each):**
- Aggregators
- Databases
- Developer Tools
- Browser Automation
- Search

**Underserved categories (2-5 servers):**
- Data Science Tools
- Legal
- Embedded Systems
- Delivery

**Categories that don't exist yet as paid x402 services:**
- Hosted agent memory (cross-session, cross-agent)
- MCP-native sandboxed code execution
- Schema validation as a service
- Structured extraction from web/docs (agent-optimized, not Bright Data pricing)
- Agent-to-agent escrow

---

## x402 Protocol State

Source: x402.org live stats (March 2026)

- 75.41M transactions
- $24.24M volume in last 30 days
- 94,060 buyers
- 22,000 sellers

Growing fast. Almost no MCP-native services taking x402 yet. The transform-agent (dashev88) is one of the earliest. First-mover position matters.

---

## Transform-Agent Gap Analysis

The existing transform-agent (github.com/dashev88/transform-agent) is a clean proof of concept.

**What it does well:**
- 43+ format pairs
- sub-50ms text conversions
- x402 payments working
- Listed on Smithery/mcp.so
- MCP + Google A2A + OpenAPI discovery
- MIT licensed, open source

**Critical gaps:**
1. Free tier cliff (100 requests) creates friction at wrong moment for automated agents
2. No streaming for large file conversions
3. No data validation endpoint
4. No schema inference
5. No input caching (same payload = same work twice)
6. No async/webhook mode for heavy document transforms
7. No agent identity tracking (wallet-based reputation)
8. Missing tools: validate, infer_schema, diff, merge, filter, sample

**Recommended additions:**
- `validate(data, schema)` → errors list
- `infer_schema(sample_data)` → JSON Schema
- `diff(v1, v2)` → changes between two datasets
- `merge(a, b, on_key)` → join two tabular datasets
- `filter(data, where_clause)` → SQL-style row filtering
- `sample(data, n)` → random row sample

These 6 tools increase average calls-per-agent from ~3 to ~20, multiplying revenue per agent without changing pricing.

---

## Opportunity Ranking

| Opportunity | Demand Signal | Competition | Technical Risk | Score |
|-------------|-------------|-------------|----------------|-------|
| Hosted Agent Memory | 67k downloads/week of local version | None (no cloud version exists) | Low | **9/10** |
| Transform Agent improvements | Proven concept | One early-stage competitor | Very Low | **8/10** |
| Sandboxed Code Execution | Every coding agent needs it | E2B (expensive, human-focused) | Medium (sandboxing is hard) | **7/10** |
| Structured Web Extraction | Universal agent need | Bright Data (expensive), Exa.ai | Low | **7/10** |
| Schema Validation Service | Every data pipeline agent | None as standalone service | Very Low | **6/10** |

**Build order:** Memory Store → Transform Agent improvements → Code Executor

---

## Why Memory Store First

1. Proven demand: 67k downloads/week on local-only version
2. Zero cloud competition
3. Low technical complexity (Redis + pgvector + FastAPI + x402 middleware)
4. Best retention: once an agent writes state to your store, switching costs are high
5. Network effects: Agent A writes, Agent B reads from A's namespace → data marketplace emerges naturally
6. Pricing math: 1k agent ops/day = $0.10/day = $3/month. Cheap enough to never cut, works at scale.
