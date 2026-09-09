# Build Report: Structured Extractor (Rank #1)

## Build Summary
- **Service:** Structured Extractor
- **Rank:** #1 of 15
- **Started:** 2026-03-03 22:00 PST
- **Completed:** 2026-03-03 22:22 PST
- **Lines of code:** 1,558 (source) + 791 (tests) = 2,349 total
- **Test count:** 38 tests
- **Test pass rate:** 38/38 (100%)

## What Was Built

| File | Lines | Purpose |
|------|-------|---------|
| `src/app/main.py` | 107 | FastAPI app — CORS, conditional x402, lifespan Redis init |
| `src/app/models/schemas.py` | 56 | Pydantic v2 request/response models for all operations |
| `src/app/extraction/fetcher.py` | 65 | Async httpx fetcher with timeout/error handling |
| `src/app/extraction/cleaner.py` | 46 | readability-lxml + BeautifulSoup fallback cleaner |
| `src/app/extraction/fast_extract.py` | 253 | JSON-LD, OpenGraph, microdata, CSS heuristic extraction |
| `src/app/extraction/llm_extract.py` | 126 | Claude Haiku fallback with smart HTML truncation (~8k tokens) |
| `src/app/extraction/image_extract.py` | 124 | Vision extraction via Claude Haiku, max 10MB images |
| `src/app/extraction/pipeline.py` | 197 | Orchestrator: cache -> fetch -> clean -> fast -> LLM -> validate |
| `src/app/middleware/cache.py` | 52 | Redis SHA256 caching, 1h TTL, graceful degradation |
| `src/app/routes/extraction.py` | 209 | All route handlers + /capabilities free endpoint |
| `src/app/routes/health.py` | 17 | Health check |
| `src/app/discovery/mcp.py` | 252 | 5 MCP tools via JSON-RPC 2.0 + .well-known/mcp.json |
| `src/app/discovery/a2a.py` | 54 | Google A2A agent card |
| `tests/test_extraction.py` | 440 | 22 unit tests — cleaner, fast extract, LLM mocking, pipeline |
| `tests/test_routes.py` | 351 | 16 integration tests — all routes, MCP, A2A |
| `Dockerfile` | — | python:3.12-slim + lxml system deps |
| `fly.toml` | — | mcp-bank-extractor, scale-to-zero, /health check |

## Feature Set

### MCP Tools (5)
1. **extract** — URL + JSON Schema -> structured JSON ($0.005 HTML / $0.015 JS)
2. **extract_from_html** — raw HTML + schema -> JSON ($0.003)
3. **extract_from_image** — image URL + schema -> JSON via vision ($0.020)
4. **extract_batch** — multiple URLs + same schema ($0.004/URL)
5. **list_capabilities** — pricing and limits (free)

### Extraction Pipeline
- **Layer 1:** JSON-LD structured data (fastest, highest confidence)
- **Layer 2:** OpenGraph meta tags
- **Layer 3:** Microdata (schema.org)
- **Layer 4:** CSS heuristic selectors (.price, h1, .title, etc.)
- **Layer 5:** Claude Haiku LLM extraction (fallback when confidence < 0.8)

### Discovery
- MCP Streamable HTTP at `/mcp`
- Google A2A agent card at `/.well-known/agent-card.json`
- OpenAPI spec at `/openapi.json`

## Profitability Case

### Pricing
| Operation | Our Price | Our Cost (est.) | Margin |
|-----------|-----------|-----------------|--------|
| extract (HTML) | $0.005 | ~$0.001 (if LLM needed) | 80%+ |
| extract (HTML, cached) | $0.0025 | ~$0 | ~100% |
| extract (JS render) | $0.015 | ~$0.003 | 80% |
| extract_from_html | $0.003 | ~$0.001 | 67% |
| extract_from_image | $0.020 | ~$0.005 (vision) | 75% |
| extract_batch | $0.004/URL | ~$0.001/URL | 75% |

### Revenue Projections [ASSUMPTIONS BELOW]
| Scale | Agents | Calls/day | Revenue/month |
|-------|--------|-----------|---------------|
| Early | 100 | 5,000 | $750 |
| Growth | 1,000 | 50,000 | $7,500 |
| Scale | 10,000 | 500,000 | $75,000 |

**Key assumptions (all unverified):**
- Average 50 extractions per agent per day [NEEDS TESTING — actual agent usage patterns unknown]
- 60% of calls hit fast extract (no LLM cost), 30% use LLM, 10% cached [NEEDS TESTING]
- $0.005 average revenue per call across all operation types [NEEDS TESTING]
- Fly.io compute at scale: ~$500-1000/month for 500k calls/day [UNVERIFIED — need load testing]

### Cost Basis
- Fly.io: $0-5/month at low volume (scale-to-zero), ~$50-500/month at scale
- Claude Haiku API: ~$0.001 per LLM extraction call (input ~2k tokens, output ~500 tokens)
- Redis: $0-15/month (Fly.io Redis or external)
- Total fixed cost: < $50/month until meaningful volume

## Traction Metrics — How to Know It's Working

### Leading Indicators (Week 1-4)
- MCP directory listing views (Smithery, mcp.so analytics)
- /mcp endpoint hits (even without payment = discovery happening)
- First paid extraction (any agent wallet making a real x402 payment)
- Unique agent wallets per day
- Ratio of fast_extract vs LLM_extract (cost efficiency indicator)

### Lagging Indicators (Month 2-3)
- Daily active agent wallets > 10
- Average calls per agent per day > 5 (sticky usage)
- Revenue > infrastructure cost (break-even)
- Repeat usage from same wallets week-over-week (retention)

### Kill Criteria
- < 5 unique wallets after 60 days of directory listing = pivot or kill
- Average confidence score < 0.5 across calls = extraction quality too low
- > 80% of calls hitting LLM fallback = fast extraction not working, margins compress

### How to Track
```bash
# Daily stats from metering logs
cat /tmp/mcp-bank-metrics.jsonl | jq -s 'group_by(.date) | map({date: .[0].date, calls: length, revenue: map(.price_usd) | add, unique_agents: [.[].agent_wallet] | unique | length})'

# Fast vs LLM ratio
cat /tmp/mcp-bank-metrics.jsonl | jq -s 'group_by(.method) | map({method: .[0].method, count: length})'
```

## Learnings

### What went well
- **Layered extraction approach** — trying JSON-LD/OpenGraph before LLM is the right architecture. Most e-commerce and news sites embed structured data, saving ~$0.001/call in LLM costs.
- **extruct library** — excellent for pulling JSON-LD, microdata, and OpenGraph in one call. Saves writing custom parsers.
- **Confidence scoring** — returning a score with each extraction lets calling agents decide if they trust the result or need to retry.

### What was harder than expected
- **CSS heuristic extraction** — field name to CSS selector mapping is fragile. "price" might be `.price`, `#price`, `[data-price]`, `.product-price`, etc. Needs real-world tuning.
- **HTML truncation for LLM** — keeping the right parts of a page (not just first N chars) requires understanding where the content likely is. The smart truncation (beginning + end + keyword-relevant sections) works but needs testing against real pages.

### What would we do differently
- Add real-world test fixtures (actual HTML from popular sites) instead of only synthetic HTML in tests
- Consider adding a feedback endpoint where agents can report bad extractions (builds training data)

### Reusable patterns extracted
- Cache middleware pattern (Redis SHA256) — identical to transform-agent, should be in shared/
- Confidence scoring model — could apply to any extraction/analysis service

## Risks & Open Questions

- **JS rendering not implemented** — render_js=true returns an error. [KNOWN GAP] Needs Playwright integration, which adds ~$5-15/month in browser instance costs.
- **Anti-bot protection** — Sites with Cloudflare/Datadome will block fetches. Not solved in v1. [KNOWN LIMITATION]
- **LLM hallucination** — Claude Haiku might fill schema fields with plausible but incorrect data. Confidence scoring mitigates but doesn't eliminate. [NEEDS REAL-WORLD TESTING]
- **extruct dependency** — pulls in rdflib which is heavy. Monitor for startup time impact.
