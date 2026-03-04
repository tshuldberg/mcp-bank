# Structured Extractor — Technical Spec

**Status:** In development
**Rank:** #1 by revenue potential ($40-60k/month at 10k agents)
**Build target:** 2-3 weeks

---

## What It Is

Given a URL (or raw HTML/image) plus a JSON Schema describing what you want, extract matching structured data and return filled JSON. MCP-native. x402-paid. No signup. No API keys.

The extraction engine tries fast CSS/heuristic extraction first. If that fails or confidence is low, it falls back to LLM-powered extraction (Claude Haiku via Anthropic API). The caller pays the same price regardless of extraction method.

---

## Why Agents Need This

Every agent doing research, competitive analysis, data collection, or monitoring needs to turn unstructured web content into structured data. Current options:
- Diffbot: $0.002-$0.01/extraction, requires account signup
- ScrapeGraph: requires self-hosting
- Running the full page through the agent's own LLM context: expensive, wastes tokens on HTML noise

This service: $0.005-$0.020/call, x402 instant payment, MCP discoverable, returns JSON matching the caller's schema.

---

## MCP Tools

### `extract`
Extract structured data from a URL matching a JSON Schema.

```json
{
  "url": "https://example.com/product/12345",
  "schema": {
    "type": "object",
    "properties": {
      "name": {"type": "string"},
      "price": {"type": "number"},
      "currency": {"type": "string"},
      "in_stock": {"type": "boolean"},
      "description": {"type": "string"}
    },
    "required": ["name", "price"]
  },
  "render_js": false
}
```

Returns:
```json
{
  "data": {
    "name": "Widget Pro",
    "price": 29.99,
    "currency": "USD",
    "in_stock": true,
    "description": "Professional-grade widget for..."
  },
  "confidence": 0.94,
  "method": "css_heuristic",
  "url": "https://example.com/product/12345",
  "extracted_at": "2026-03-04T01:00:00Z",
  "duration_ms": 450
}
```

Price: **$0.005** (HTML-only) / **$0.015** (JS-rendered)

---

### `extract_from_html`
Same as `extract` but accepts raw HTML string instead of URL. Useful when the agent already has the HTML.

```json
{
  "html": "<html>...</html>",
  "schema": {
    "type": "object",
    "properties": {
      "title": {"type": "string"},
      "author": {"type": "string"},
      "published_date": {"type": "string", "format": "date"}
    }
  }
}
```

Price: **$0.003** (no fetch needed)

---

### `extract_from_image`
Extract structured data from an image URL using vision LLM.

```json
{
  "image_url": "https://example.com/screenshot.png",
  "schema": {
    "type": "object",
    "properties": {
      "text_content": {"type": "string"},
      "prices": {"type": "array", "items": {"type": "number"}},
      "has_table": {"type": "boolean"}
    }
  }
}
```

Price: **$0.020** (vision model required)

---

### `extract_batch`
Extract from multiple URLs with the same schema. Returns array of results.

```json
{
  "urls": ["https://example.com/product/1", "https://example.com/product/2"],
  "schema": {...},
  "render_js": false,
  "max_concurrent": 5
}
```

Price: **$0.004/URL** (batch discount)

---

### `list_capabilities`
Returns supported extraction types, pricing, and limits. Free.

---

## Extraction Pipeline

```
Input (URL + Schema)
    │
    ▼
[1. Fetch] ──────── httpx for HTML-only, Playwright for JS-rendered
    │
    ▼
[2. Clean] ──────── Remove nav, footer, ads, scripts, styles (Readability algorithm)
    │
    ▼
[3. CSS Extract] ── Try schema-aware CSS selectors + microdata/JSON-LD/OpenGraph
    │                 If confidence >= 0.8, return result
    ▼
[4. LLM Extract] ── Send cleaned HTML + schema to Claude Haiku
    │                 Parse structured response, validate against schema
    ▼
[5. Validate] ───── jsonschema validation against caller's schema
    │                 Fill missing optional fields with null
    ▼
[6. Return] ──────── JSON result with confidence score + extraction method
```

### Step 3 Details: CSS/Heuristic Extraction

Before using an LLM, try these fast extraction paths:
1. **JSON-LD** — Many sites embed structured data as `<script type="application/ld+json">`. Parse it, map to schema.
2. **OpenGraph/Meta** — `<meta property="og:title">`, `<meta name="description">`, etc.
3. **Microdata** — `itemprop`, `itemscope`, `itemtype` attributes.
4. **Schema.org** — Look for schema.org types matching the requested schema fields.
5. **Common CSS patterns** — Price: `.price`, `[data-price]`, `#price`. Title: `h1`, `.product-title`. Image: `.product-image img[src]`.

If any path produces data matching >= 80% of required schema fields with reasonable confidence, use it. Otherwise, fall through to LLM.

### Step 4 Details: LLM Extraction

System prompt:
```
You are a structured data extractor. Given HTML content and a JSON Schema, extract data matching the schema. Return ONLY valid JSON matching the schema. If a field cannot be determined, use null. Do not hallucinate data that isn't present in the content.
```

Model: Claude Haiku (cheapest, fastest, sufficient for extraction)
Max input: 8000 tokens of cleaned HTML (truncate intelligently — keep beginning + end + schema-relevant sections)
Cost per call: ~$0.001 (Haiku pricing)
Our price: $0.005-$0.015 (5-15x markup covers infrastructure + margin)

---

## Endpoints

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/extract` | Extract from URL + schema | x402 |
| POST | `/extract/html` | Extract from raw HTML + schema | x402 |
| POST | `/extract/image` | Extract from image + schema | x402 |
| POST | `/extract/batch` | Batch extract from URLs | x402 |
| GET | `/capabilities` | Pricing and limits | Free |
| POST | `/mcp` | MCP Streamable HTTP | — |
| GET | `/.well-known/agent-card.json` | Google A2A | — |
| GET | `/openapi.json` | OpenAPI spec | — |
| GET | `/health` | Health check | — |

---

## Pricing

| Operation | Price | Notes |
|-----------|-------|-------|
| `extract(url)` HTML-only | $0.005 | CSS-first, LLM fallback |
| `extract(url, render_js=true)` | $0.015 | Playwright + extraction |
| `extract_from_html(html)` | $0.003 | No fetch, extraction only |
| `extract_from_image(image_url)` | $0.020 | Vision model required |
| `extract_batch(urls)` per URL | $0.004 | Batch discount |
| `list_capabilities` | Free | Always free |

---

## Dependencies

```
fastapi, uvicorn, orjson, pydantic>=2.0
httpx                 # async HTTP for fetching
playwright            # JS rendering (optional, for render_js=true)
beautifulsoup4        # HTML parsing
readability-lxml      # content extraction (Mozilla Readability port)
lxml                  # HTML/XML processing
jsonschema            # schema validation
anthropic             # Claude Haiku API for LLM extraction
x402                  # payment middleware
redis[asyncio]        # caching extracted results
python-dotenv
extruct               # structured data extraction (JSON-LD, microdata, OpenGraph)
```

---

## Caching Strategy

Cache key: SHA-256 of (url + schema_hash + render_js)
Cache TTL: 1 hour (web content changes)
Cached results: served at 50% price

---

## Rate Limits

- 100 concurrent extractions per agent wallet
- 10 concurrent JS-rendered extractions (Playwright browser pool limit)
- Batch: max 50 URLs per request

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `WALLET_ADDRESS` | Yes | USDC destination on Base |
| `CDP_API_KEY_ID` | Yes | Coinbase CDP for x402 |
| `CDP_API_KEY_SECRET` | Yes | Coinbase CDP secret |
| `ANTHROPIC_API_KEY` | Yes | Claude Haiku for LLM extraction |
| `REDIS_URL` | No | Cache (graceful degradation without it) |
| `ADMIN_KEY` | Yes | Admin operations |
| `PLAYWRIGHT_BROWSERS_PATH` | No | Custom browser path for Playwright |

---

## Confidence Scoring

Each extraction returns a confidence score (0.0-1.0):
- **0.9-1.0:** JSON-LD or structured data found and fully matched schema
- **0.7-0.9:** CSS heuristics matched most fields with high confidence
- **0.5-0.7:** LLM extraction with partial schema coverage
- **0.3-0.5:** LLM extraction with low coverage or ambiguous fields
- **< 0.3:** Extraction largely failed, most fields null

Confidence is computed as: (matched_required_fields / total_required_fields) * field_confidence_avg

---

## Open Questions

- [ ] Should we self-host Playwright or use a browser-as-a-service (Browserless.io)?
  Lean: Self-host on Fly.io with persistent Playwright instance for cost control.
- [ ] Should we proxy to multiple LLM providers or just Anthropic?
  Lean: Anthropic-only for now (Haiku is cheapest + fastest for extraction tasks).
- [ ] Do we need anti-bot bypass for protected sites?
  Lean: Not in v1. Agents should use a separate proxy/crawler service for protected sites. We handle public content.
