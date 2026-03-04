"""Unit tests for transform functions — no HTTP, no payments."""

import pytest
import orjson

from src.app.transforms import tabular, markup, encoding
from src.app.transforms.schema_ops import (
    validate_data,
    infer_schema,
    reshape_json,
    diff_data,
    merge_data,
    filter_data,
    sample_data,
)
from src.app.transforms.registry import get_handler, get_price, list_capabilities


# ─── Tabular ──────────────────────────────────────────────────────────────────

def test_json_to_csv():
    data = '[{"name":"Alice","age":30},{"name":"Bob","age":25}]'
    result = tabular.json_to_csv(data)
    assert "name" in result
    assert "Alice" in result
    assert "Bob" in result


def test_csv_to_json():
    csv = "name,age\nAlice,30\nBob,25\n"
    result = orjson.loads(tabular.csv_to_json(csv))
    assert len(result) == 2
    assert result[0]["name"] == "Alice"


def test_json_to_xml():
    data = '[{"id":1,"value":"x"}]'
    result = tabular.json_to_xml(data)
    assert "<root>" in result
    assert "<id>1</id>" in result


def test_xml_to_json():
    xml = "<root><item><id>1</id><name>Alice</name></item></root>"
    result = orjson.loads(tabular.xml_to_json(xml))
    assert result[0]["id"] == "1"
    assert result[0]["name"] == "Alice"


def test_json_to_yaml():
    data = '{"key": "value"}'
    result = tabular.json_to_yaml(data)
    assert "key: value" in result


def test_yaml_to_json():
    yaml = "key: value\nnum: 42\n"
    result = orjson.loads(tabular.yaml_to_json(yaml))
    assert result["key"] == "value"
    assert result["num"] == 42


def test_json_to_toml():
    data = '{"title": "hello", "count": 5}'
    result = tabular.json_to_toml(data)
    assert 'title = "hello"' in result


def test_toml_to_json():
    toml = 'title = "hello"\ncount = 5\n'
    result = orjson.loads(tabular.toml_to_json(toml))
    assert result["title"] == "hello"
    assert result["count"] == 5


def test_csv_to_xml():
    csv = "id,name\n1,Alice\n2,Bob\n"
    result = tabular.csv_to_xml(csv)
    assert "<root>" in result
    assert "Alice" in result


def test_xml_to_csv():
    xml = "<root><item><id>1</id><name>Alice</name></item><item><id>2</id><name>Bob</name></item></root>"
    result = tabular.xml_to_csv(xml)
    assert "id" in result
    assert "Alice" in result


# ─── Markup ───────────────────────────────────────────────────────────────────

def test_html_to_text():
    html = "<html><body><h1>Title</h1><p>Hello world</p></body></html>"
    result = markup.html_to_text(html)
    assert "Title" in result
    assert "Hello world" in result


def test_html_to_markdown():
    html = "<h1>Title</h1><p>Body text</p>"
    result = markup.html_to_markdown(html)
    assert "# Title" in result
    assert "Body text" in result


def test_markdown_to_html():
    md = "# Hello\n\nWorld"
    result = markup.markdown_to_html(md)
    assert "<h1>" in result
    assert "Hello" in result


def test_text_to_html():
    text = "Hello <World>"
    result = markup.text_to_html(text)
    assert "<pre>" in result
    assert "&lt;World&gt;" in result


# ─── Encoding ─────────────────────────────────────────────────────────────────

def test_base64_roundtrip():
    original = "Hello, World!"
    encoded = encoding.to_base64(original)
    assert encoding.from_base64(encoded) == original


def test_hex_roundtrip():
    original = "deadbeef"
    encoded = encoding.to_hex(original)
    assert encoding.from_hex(encoded) == original


def test_url_roundtrip():
    original = "hello world & more"
    encoded = encoding.to_url_encoded(original)
    assert " " not in encoded
    assert encoding.from_url_encoded(encoded) == original


# ─── Schema ops ───────────────────────────────────────────────────────────────

def test_validate_valid():
    data = '{"name": "Alice", "age": 30}'
    schema = '{"type": "object", "properties": {"name": {"type": "string"}, "age": {"type": "integer"}}, "required": ["name", "age"]}'
    result = validate_data(data, schema)
    assert result["valid"] is True
    assert result["errors"] == []


def test_validate_invalid():
    data = '{"name": "Alice", "age": "thirty"}'
    schema = '{"type": "object", "properties": {"age": {"type": "integer"}}, "required": ["name", "age"]}'
    result = validate_data(data, schema)
    assert result["valid"] is False
    assert len(result["errors"]) > 0


def test_infer_schema_array():
    data = '[{"name":"Alice","age":30},{"name":"Bob","age":25,"city":"Paris"}]'
    result = infer_schema(data)
    schema = result["schema"]
    assert schema["type"] == "array"
    props = schema["items"]["properties"]
    assert "name" in props
    assert "age" in props
    assert result["confidence"] > 0


def test_reshape():
    data = {"user": {"profile": {"name": "Alice"}, "address": {"city": "Paris"}}}
    mapping = {"name": "user.profile.name", "city": "user.address.city"}
    result = reshape_json(data, mapping)
    assert result["result"]["name"] == "Alice"
    assert result["result"]["city"] == "Paris"
    assert result["fields_mapped"] == 2
    assert result["fields_missing"] == []


def test_reshape_missing_field():
    data = {"user": {"name": "Alice"}}
    mapping = {"name": "user.name", "city": "user.address.city"}
    result = reshape_json(data, mapping)
    assert result["fields_mapped"] == 1
    assert "user.address.city" in result["fields_missing"]


def test_diff():
    before = '[{"id":1,"status":"active"},{"id":2,"status":"active"}]'
    after = '[{"id":1,"status":"inactive"},{"id":3,"status":"active"}]'
    result = diff_data(before, after, "id")
    assert len(result["added"]) == 1
    assert result["added"][0]["id"] == 3
    assert len(result["removed"]) == 1
    assert result["removed"][0]["id"] == 2
    assert len(result["modified"]) == 1
    assert result["modified"][0]["field"] == "status"


def test_merge_inner():
    left = '[{"id":1,"name":"Alice"},{"id":2,"name":"Bob"}]'
    right = '[{"id":1,"city":"Paris"},{"id":3,"city":"London"}]'
    result = merge_data(left, right, "id", "inner")
    rows = orjson.loads(result["result"])
    assert len(rows) == 1
    assert rows[0]["name"] == "Alice"
    assert rows[0]["city"] == "Paris"
    assert result["rows_out"] == 1


def test_filter_gte():
    data = '[{"name":"Alice","age":30},{"name":"Bob","age":17}]'
    result = filter_data(data, "age >= 18")
    rows = orjson.loads(result["result"])
    assert len(rows) == 1
    assert rows[0]["name"] == "Alice"
    assert result["rows_in"] == 2
    assert result["rows_out"] == 1


def test_filter_eq():
    data = '[{"name":"Alice","status":"active"},{"name":"Bob","status":"inactive"}]'
    result = filter_data(data, "status == active")
    rows = orjson.loads(result["result"])
    assert len(rows) == 1
    assert rows[0]["name"] == "Alice"


def test_sample():
    data = orjson.dumps([{"id": i} for i in range(100)]).decode()
    result = sample_data(data, n=10, seed=42)
    rows = orjson.loads(result["result"])
    assert len(rows) == 10
    assert result["rows_in"] == 100


def test_sample_reproducible():
    data = orjson.dumps([{"id": i} for i in range(100)]).decode()
    r1 = sample_data(data, n=5, seed=42)
    r2 = sample_data(data, n=5, seed=42)
    assert r1["result"] == r2["result"]


# ─── Registry ─────────────────────────────────────────────────────────────────

def test_get_handler_exact():
    handler = get_handler("json", "csv")
    assert handler is not None
    assert callable(handler)


def test_get_handler_wildcard_target():
    handler = get_handler("json", "base64")
    assert handler is not None


def test_get_handler_wildcard_source():
    handler = get_handler("base64", "anything")
    assert handler is not None


def test_get_handler_unsupported():
    handler = get_handler("json", "docx")
    assert handler is None


def test_get_price_text():
    price = get_price("json", "csv")
    assert price == 0.001


def test_get_price_document():
    price = get_price("pdf", "text")
    assert price == 0.005


def test_list_capabilities():
    caps = list_capabilities()
    assert len(caps) > 10
    names = [(c["source_format"], c["target_format"]) for c in caps]
    assert ("json", "csv") in names
