# Structured Extractor

URL + JSON Schema -> structured data. MCP-native. x402-paid. No signup.

**Status:** In development — [see spec](./SPEC.md)

---

## The Problem

Agents need structured data from the web constantly. Product prices, contact info, event details, article metadata. The web serves HTML. Agents need JSON. Current options require account signup and API keys. This service takes a URL and a schema, returns filled JSON, and charges $0.005/call via x402.

---

## MCP Config

```json
{
  "mcpServers": {
    "mcp-bank-extractor": {
      "url": "https://extractor.mcp-bank.fly.dev/mcp"
    }
  }
}
```

---

## Tools

| Tool | Description | Price |
|------|-------------|-------|
| `extract` | URL + JSON Schema -> structured JSON | $0.005 (HTML) / $0.015 (JS) |
| `extract_from_html` | Raw HTML + schema -> JSON | $0.003 |
| `extract_from_image` | Image + schema -> JSON (vision) | $0.020 |
| `extract_batch` | Multiple URLs + same schema | $0.004/URL |
| `list_capabilities` | Pricing and limits | Free |

---

## How It Works

1. Fetch the URL (httpx for HTML, Playwright for JS-rendered pages)
2. Clean the HTML (Readability algorithm — strips nav, ads, scripts)
3. Try fast extraction first: JSON-LD, OpenGraph, microdata, CSS selectors
4. If fast path confidence < 80%, fall back to Claude Haiku LLM extraction
5. Validate result against caller's JSON Schema
6. Return structured JSON with confidence score

Every response includes `confidence` (0.0-1.0) and `method` (css_heuristic | json_ld | llm) so the agent knows how the data was extracted.
