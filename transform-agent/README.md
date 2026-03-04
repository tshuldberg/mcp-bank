# Transform Agent

Stateless data format conversion and transformation. MCP-native. x402-paid. No signup.

**Status:** In development — [see spec](./SPEC.md)

---

## Formats

| Category | Formats |
|----------|---------|
| Structured | JSON, CSV, XML, YAML, TOML |
| Markup | HTML, Markdown, Plain Text |
| Documents | PDF, Excel (.xlsx), DOCX |
| Encoding | Base64, URL-encoded, Hex |

Any-to-any conversion where a logical path exists.

---

## Tools

| Tool | Description | Price |
|------|-------------|-------|
| `transform` | Convert between any two supported formats | $0.001 (text) / $0.005 (docs) |
| `validate` | Check data against a schema, return errors | $0.0005 |
| `infer_schema` | Generate JSON Schema from sample data | $0.0005 |
| `reshape_json` | Restructure nested JSON with dot-notation mapping | $0.002 |
| `diff` | Show changes between two datasets | $0.001 |
| `merge` | Combine two tabular datasets on a key | $0.001 |
| `filter` | SQL-style WHERE filtering on tabular data | $0.001 |
| `sample` | Return N random rows from a dataset | $0.0005 |
| `list_capabilities` | List all supported conversions with pricing | Free |

---

## MCP Config

```json
{
  "mcpServers": {
    "mcp-bank-transform": {
      "url": "https://transform.mcp-bank.fly.dev/mcp"
    }
  }
}
```

---

## Quick Start

```bash
# Convert JSON to CSV
curl -X POST https://transform.mcp-bank.fly.dev/transform \
  -H "Content-Type: application/json" \
  -H "X-Payment: <x402_payment_header>" \
  -d '{
    "source_format": "json",
    "target_format": "csv",
    "data": "[{\"name\":\"Alice\",\"age\":30},{\"name\":\"Bob\",\"age\":25}]"
  }'

# Validate against a schema
curl -X POST https://transform.mcp-bank.fly.dev/validate \
  -H "Content-Type: application/json" \
  -H "X-Payment: <x402_payment_header>" \
  -d '{
    "data": "{\"name\": \"Alice\", \"age\": \"thirty\"}",
    "schema": "{\"type\": \"object\", \"properties\": {\"age\": {\"type\": \"integer\"}}}"
  }'
```

---

## How We Differ from the Existing Transform Agent

The dashev88/transform-agent is a clean proof of concept. Our build addresses its gaps:

- **No free tier cliff.** Micropayments from request 1 — no 100-request cliff that forces payment setup before the agent has proven value.
- **Streaming.** Large file conversions stream output instead of blocking the connection.
- **Caching.** Identical input hash → skip recompute, return cached output.
- **Async/webhook.** Heavy document transforms (PDF → JSON) return a job ID and call a webhook on completion.
- **Wallet identity.** Agent identifies by CDP wallet, not API key. Enables reputation, history, volume discounts.
- **Extended tools.** validate, infer_schema, diff, merge, filter, sample — the operations every data pipeline agent actually needs beyond raw format conversion.
