# Transform Agent — Technical Spec

**Status:** In development
**Target deploy:** 3 weeks from Memory Store launch

---

## Core Philosophy

Stateless. Every request is independent. No session state. No user accounts. Payment via wallet identity.

Fast for text (<50ms). Async for documents (webhook on completion).

---

## Format Registry

```python
SUPPORTED_FORMATS = {
    "structured": ["json", "csv", "xml", "yaml", "toml"],
    "markup":     ["html", "markdown", "text"],
    "documents":  ["pdf", "xlsx", "docx"],
    "encoding":   ["base64", "url", "hex"],
}

# Valid conversion paths (not all pairs are logical)
CONVERSION_MATRIX = {
    ("json", "csv"):      tabular.json_to_csv,
    ("json", "xml"):      tabular.json_to_xml,
    ("json", "yaml"):     tabular.json_to_yaml,
    ("json", "toml"):     tabular.json_to_toml,
    ("csv", "json"):      tabular.csv_to_json,
    ("csv", "xml"):       tabular.csv_to_xml,
    ("xml", "json"):      tabular.xml_to_json,
    ("xml", "csv"):       tabular.xml_to_csv,
    ("yaml", "json"):     tabular.yaml_to_json,
    ("toml", "json"):     tabular.toml_to_json,
    ("html", "markdown"): markup.html_to_markdown,
    ("html", "text"):     markup.html_to_text,
    ("markdown", "html"): markup.markdown_to_html,
    ("pdf", "text"):      documents.pdf_to_text,
    ("pdf", "json"):      documents.pdf_to_json,
    ("xlsx", "csv"):      documents.xlsx_to_csv,
    ("xlsx", "json"):     documents.xlsx_to_json,
    ("docx", "text"):     documents.docx_to_text,
    ("docx", "markdown"): documents.docx_to_markdown,
    # encoding
    ("*", "base64"):      encoding.to_base64,
    ("base64", "*"):      encoding.from_base64,
    ("*", "hex"):         encoding.to_hex,
    ("*", "url"):         encoding.to_url_encoded,
    # ... 43+ total pairs
}
```

---

## API Endpoints

### POST `/transform`

Synchronous for text formats (<50ms). Async for documents (returns job ID).

**Request:**
```json
{
  "source_format": "json",
  "target_format": "csv",
  "data": "[{\"name\":\"Alice\",\"age\":30}]",
  "async": false,
  "webhook_url": null
}
```

**Response (sync):**
```json
{
  "result": "name,age\nAlice,30",
  "source_format": "json",
  "target_format": "csv",
  "bytes_in": 28,
  "bytes_out": 15,
  "cached": false,
  "duration_ms": 3
}
```

**Response (async):**
```json
{
  "job_id": "job_abc123",
  "status": "queued",
  "poll_url": "/jobs/job_abc123",
  "estimated_seconds": 5
}
```

---

### POST `/validate`

Check data against JSON Schema. Returns validation errors.

**Request:**
```json
{
  "data": "{\"name\": \"Alice\", \"age\": \"thirty\"}",
  "schema": "{\"type\": \"object\", \"properties\": {\"age\": {\"type\": \"integer\"}}, \"required\": [\"name\", \"age\"]}",
  "data_format": "json"
}
```

**Response:**
```json
{
  "valid": false,
  "errors": [
    {"path": "$.age", "message": "Expected integer, got string", "value": "thirty"}
  ]
}
```

---

### POST `/infer_schema`

Generate a JSON Schema from sample data.

**Request:**
```json
{
  "data": "[{\"name\":\"Alice\",\"age\":30},{\"name\":\"Bob\",\"age\":25,\"city\":\"Paris\"}]",
  "data_format": "json",
  "strictness": "relaxed"
}
```

**Response:**
```json
{
  "schema": {
    "type": "array",
    "items": {
      "type": "object",
      "properties": {
        "name": {"type": "string"},
        "age": {"type": "integer"},
        "city": {"type": "string"}
      },
      "required": ["name", "age"]
    }
  },
  "confidence": 0.91
}
```

---

### POST `/diff`

Compare two datasets and return changes.

**Request:**
```json
{
  "before": "[{\"id\":1,\"status\":\"active\"},{\"id\":2,\"status\":\"active\"}]",
  "after": "[{\"id\":1,\"status\":\"inactive\"},{\"id\":3,\"status\":\"active\"}]",
  "data_format": "json",
  "key_field": "id"
}
```

**Response:**
```json
{
  "added": [{"id": 3, "status": "active"}],
  "removed": [{"id": 2, "status": "active"}],
  "modified": [{"id": 1, "field": "status", "before": "active", "after": "inactive"}],
  "unchanged": 0
}
```

---

### POST `/merge`

Combine two tabular datasets.

**Request:**
```json
{
  "left": "[{\"id\":1,\"name\":\"Alice\"}]",
  "right": "[{\"id\":1,\"city\":\"Paris\"}]",
  "on": "id",
  "how": "inner",
  "data_format": "json"
}
```

**Response:**
```json
{
  "result": "[{\"id\":1,\"name\":\"Alice\",\"city\":\"Paris\"}]",
  "rows_in_left": 1,
  "rows_in_right": 1,
  "rows_out": 1
}
```

---

### POST `/filter`

Filter rows with a simple expression language.

**Request:**
```json
{
  "data": "[{\"name\":\"Alice\",\"age\":30},{\"name\":\"Bob\",\"age\":17}]",
  "where": "age >= 18",
  "data_format": "json"
}
```

**Response:**
```json
{
  "result": "[{\"name\":\"Alice\",\"age\":30}]",
  "rows_in": 2,
  "rows_out": 1
}
```

---

### POST `/reshape`

Restructure nested JSON using dot-notation path mapping.

**Request:**
```json
{
  "data": {"user": {"profile": {"name": "Alice"}, "address": {"city": "Paris"}}},
  "mapping": {"name": "user.profile.name", "city": "user.address.city"}
}
```

**Response:**
```json
{"name": "Alice", "city": "Paris"}
```

---

## Caching

Input is hashed (SHA-256 of `source_format + target_format + data`). Cache hit → return stored result, no compute. Cache TTL: 1 hour. Cache backend: Redis.

Cached results are served at full speed but charged at 50% price (agent gets cheaper repeat calls, we get free compute).

---

## Async Document Processing

Documents (PDF, DOCX, XLSX) trigger async mode automatically when `data` exceeds 100KB, or when `async: true` is set.

```
POST /transform → {job_id: "job_abc"}
GET  /jobs/job_abc → {status: "processing", progress: 0.6}
GET  /jobs/job_abc → {status: "complete", result_url: "/results/job_abc"}
```

Webhook called on completion if `webhook_url` provided.

---

## Pricing

| Operation | Price |
|-----------|-------|
| Text format transform | $0.001 |
| Document transform | $0.005 |
| Validate | $0.0005 |
| Infer schema | $0.0005 |
| Reshape JSON | $0.002 |
| Diff | $0.001 |
| Merge | $0.001 |
| Filter | $0.001 |
| Sample | $0.0005 |
| Cached result | 50% of standard price |
| List capabilities | Free |

---

## Dependencies

```
fastapi, uvicorn, orjson, pydantic
polars          # fast tabular operations
lxml            # XML processing
ruamel.yaml     # YAML with round-trip support
tomllib         # TOML parsing (stdlib 3.11+)
tomli-w         # TOML writing
pymupdf         # PDF extraction
openpyxl        # Excel read/write
python-docx     # DOCX processing
markdown-it-py  # Markdown parsing
beautifulsoup4  # HTML processing
jsonschema      # JSON Schema validation
x402            # payment middleware
redis           # caching
```
