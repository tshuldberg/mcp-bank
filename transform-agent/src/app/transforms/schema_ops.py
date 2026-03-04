"""
Schema and data operations: validate, infer_schema, reshape, diff, merge, filter, sample.
"""

import re
import io
import orjson
import polars as pl
import jsonschema
from jsonschema import Draft7Validator


# ─── Validate ─────────────────────────────────────────────────────────────────

def validate_data(data: str, schema: str) -> dict:
    """Validate JSON data against a JSON Schema. Returns {valid, errors}."""
    parsed_data = orjson.loads(data)
    parsed_schema = orjson.loads(schema)
    validator = Draft7Validator(parsed_schema)
    errors = []
    for error in sorted(validator.iter_errors(parsed_data), key=str):
        path = "$.{}".format(".".join(str(p) for p in error.absolute_path)) if error.absolute_path else "$"
        errors.append({
            "path": path,
            "message": error.message,
            "value": error.instance,
        })
    return {"valid": len(errors) == 0, "errors": errors}


# ─── Infer Schema ─────────────────────────────────────────────────────────────

def _infer_type(value) -> dict:
    if value is None:
        return {"type": "null"}
    if isinstance(value, bool):
        return {"type": "boolean"}
    if isinstance(value, int):
        return {"type": "integer"}
    if isinstance(value, float):
        return {"type": "number"}
    if isinstance(value, str):
        return {"type": "string"}
    if isinstance(value, list):
        if not value:
            return {"type": "array", "items": {}}
        item_schemas = [_infer_type(v) for v in value]
        # merge item types
        types = {s.get("type") for s in item_schemas}
        if len(types) == 1:
            return {"type": "array", "items": item_schemas[0]}
        return {"type": "array", "items": {"type": list(types)}}
    if isinstance(value, dict):
        return _infer_object_schema([value], strictness="relaxed")
    return {}


def _infer_object_schema(records: list[dict], strictness: str = "relaxed") -> dict:
    all_keys: set[str] = set()
    key_types: dict[str, set] = {}
    key_presence: dict[str, int] = {}

    for record in records:
        for k, v in record.items():
            all_keys.add(k)
            type_str = _infer_type(v).get("type", "string")
            key_types.setdefault(k, set()).add(str(type_str))
            key_presence[k] = key_presence.get(k, 0) + 1

    properties = {}
    for key in all_keys:
        types = key_types[key]
        if len(types) == 1:
            properties[key] = {"type": next(iter(types))}
        else:
            properties[key] = {"type": sorted(types)}

    if strictness == "strict":
        required = [k for k in all_keys if key_presence.get(k, 0) == len(records)]
    else:
        # relaxed: required only if present in >80% of records
        required = [k for k in all_keys if key_presence.get(k, 0) / max(len(records), 1) > 0.8]

    schema: dict = {"type": "object", "properties": properties}
    if required:
        schema["required"] = sorted(required)
    return schema


def infer_schema(data: str, data_format: str = "json", strictness: str = "relaxed") -> dict:
    """Infer a JSON Schema from sample data. Returns {schema, confidence}."""
    parsed = orjson.loads(data)

    if isinstance(parsed, list):
        if not parsed:
            return {"schema": {"type": "array", "items": {}}, "confidence": 0.5}
        if all(isinstance(r, dict) for r in parsed):
            item_schema = _infer_object_schema(parsed, strictness)
            schema = {"type": "array", "items": item_schema}
        else:
            schema = {"type": "array", "items": _infer_type(parsed[0])}
        # confidence based on consistency
        total_keys = sum(len(r) for r in parsed if isinstance(r, dict))
        expected_keys = len(item_schema.get("properties", {})) * len(parsed)
        confidence = min(1.0, total_keys / max(expected_keys, 1)) if expected_keys else 0.7
    elif isinstance(parsed, dict):
        schema = _infer_object_schema([parsed], strictness)
        confidence = 0.85
    else:
        schema = _infer_type(parsed)
        confidence = 0.95

    return {"schema": schema, "confidence": round(confidence, 2)}


# ─── Reshape ──────────────────────────────────────────────────────────────────

def _get_nested(obj: dict, path: str):
    """Extract a value using dot-notation path."""
    parts = path.split(".")
    current = obj
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


def reshape_json(data, mapping: dict[str, str]) -> dict:
    """
    Reshape JSON using dot-notation path mapping.
    mapping: {output_key: "dot.path.to.source"}
    Returns {result, fields_mapped, fields_missing}.
    """
    if isinstance(data, str):
        data = orjson.loads(data)

    result = {}
    fields_missing = []
    for out_key, src_path in mapping.items():
        value = _get_nested(data, src_path)
        if value is None:
            fields_missing.append(src_path)
        result[out_key] = value

    fields_mapped = len(mapping) - len(fields_missing)
    return {"result": result, "fields_mapped": fields_mapped, "fields_missing": fields_missing}


# ─── Diff ─────────────────────────────────────────────────────────────────────

def diff_data(before: str, after: str, key_field: str) -> dict:
    """Compare two JSON datasets. Returns {added, removed, modified, unchanged}."""
    before_list = orjson.loads(before)
    after_list = orjson.loads(after)

    before_map = {row[key_field]: row for row in before_list if key_field in row}
    after_map = {row[key_field]: row for row in after_list if key_field in row}

    before_keys = set(before_map.keys())
    after_keys = set(after_map.keys())

    added = [after_map[k] for k in after_keys - before_keys]
    removed = [before_map[k] for k in before_keys - after_keys]
    modified = []
    unchanged = 0

    for k in before_keys & after_keys:
        b_row = before_map[k]
        a_row = after_map[k]
        row_changed = False
        for field in set(b_row.keys()) | set(a_row.keys()):
            if field == key_field:
                continue
            b_val = b_row.get(field)
            a_val = a_row.get(field)
            if b_val != a_val:
                modified.append({
                    "id": k,
                    "field": field,
                    "before": b_val,
                    "after": a_val,
                })
                row_changed = True
        if not row_changed:
            unchanged += 1

    return {"added": added, "removed": removed, "modified": modified, "unchanged": unchanged}


# ─── Merge ────────────────────────────────────────────────────────────────────

def merge_data(left: str, right: str, on: str, how: str = "inner") -> dict:
    """Merge two JSON datasets using polars join."""
    left_list = orjson.loads(left)
    right_list = orjson.loads(right)

    df_left = pl.DataFrame(left_list)
    df_right = pl.DataFrame(right_list)

    how_map = {"inner": "inner", "left": "left", "right": "right", "full": "full"}
    join_how = how_map.get(how, "inner")

    merged = df_left.join(df_right, on=on, how=join_how)  # type: ignore[arg-type]
    result = orjson.dumps(merged.to_dicts()).decode()

    return {
        "result": result,
        "rows_in_left": len(left_list),
        "rows_in_right": len(right_list),
        "rows_out": len(merged),
    }


# ─── Filter ───────────────────────────────────────────────────────────────────

_OPS = {
    ">=": lambda a, b: a >= b,
    "<=": lambda a, b: a <= b,
    "!=": lambda a, b: a != b,
    "==": lambda a, b: a == b,
    ">":  lambda a, b: a > b,
    "<":  lambda a, b: a < b,
}

_FILTER_RE = re.compile(r"^\s*(\w+)\s*(>=|<=|!=|==|>|<)\s*(.+)\s*$")


def _coerce(value: str):
    """Try to coerce a string to int, float, or leave as string."""
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value.strip().strip("'\"")


def filter_data(data: str, where: str) -> dict:
    """Filter rows using a simple expression: 'field op value'."""
    records = orjson.loads(data)
    rows_in = len(records)

    match = _FILTER_RE.match(where)
    if not match:
        raise ValueError(f"Cannot parse filter expression: {where!r}")

    field, op, raw_value = match.group(1), match.group(2), match.group(3)
    cmp_value = _coerce(raw_value)
    fn = _OPS[op]

    result = []
    for row in records:
        row_val = row.get(field)
        if row_val is None:
            continue
        try:
            if fn(row_val, cmp_value):
                result.append(row)
        except TypeError:
            # type mismatch — skip row
            pass

    return {
        "result": orjson.dumps(result).decode(),
        "rows_in": rows_in,
        "rows_out": len(result),
    }


# ─── Sample ───────────────────────────────────────────────────────────────────

def sample_data(data: str, n: int = 10, seed: int | None = None) -> dict:
    """Sample n rows from a JSON dataset."""
    records = orjson.loads(data)
    rows_in = len(records)

    df = pl.DataFrame(records)
    sampled = df.sample(n=min(n, len(df)), seed=seed, with_replacement=False)
    result = orjson.dumps(sampled.to_dicts()).decode()

    return {
        "result": result,
        "rows_in": rows_in,
        "rows_out": len(sampled),
    }
