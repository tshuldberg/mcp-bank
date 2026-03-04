"""
Tabular format conversions using polars.
All functions accept and return strings.
Binary-format inputs (pdf, xlsx, docx) are handled in documents.py.
"""

import io
import orjson
import polars as pl
from ruamel.yaml import YAML
import tomli_w
import tomllib
from lxml import etree


def _df_from_json(data: str) -> pl.DataFrame:
    parsed = orjson.loads(data)
    if isinstance(parsed, dict):
        parsed = [parsed]
    return pl.DataFrame(parsed)


def _df_to_json(df: pl.DataFrame) -> str:
    return orjson.dumps(df.to_dicts()).decode()


# ─── JSON conversions ─────────────────────────────────────────────────────────

def json_to_csv(data: str) -> str:
    df = _df_from_json(data)
    buf = io.StringIO()
    df.write_csv(buf)
    return buf.getvalue()


def json_to_xml(data: str) -> str:
    records = orjson.loads(data)
    if isinstance(records, dict):
        records = [records]
    root = etree.Element("root")
    for record in records:
        item = etree.SubElement(root, "item")
        for key, value in record.items():
            child = etree.SubElement(item, str(key))
            child.text = str(value) if value is not None else ""
    return etree.tostring(root, pretty_print=True, encoding="unicode")


def json_to_yaml(data: str) -> str:
    parsed = orjson.loads(data)
    yaml = YAML()
    yaml.default_flow_style = False
    buf = io.StringIO()
    yaml.dump(parsed, buf)
    return buf.getvalue()


def json_to_toml(data: str) -> str:
    parsed = orjson.loads(data)
    if isinstance(parsed, list):
        parsed = {"items": parsed}
    return tomli_w.dumps(parsed)


# ─── CSV conversions ──────────────────────────────────────────────────────────

def csv_to_json(data: str) -> str:
    df = pl.read_csv(io.StringIO(data))
    return _df_to_json(df)


def csv_to_xml(data: str) -> str:
    df = pl.read_csv(io.StringIO(data))
    root = etree.Element("root")
    for row in df.to_dicts():
        item = etree.SubElement(root, "item")
        for key, value in row.items():
            child = etree.SubElement(item, str(key))
            child.text = str(value) if value is not None else ""
    return etree.tostring(root, pretty_print=True, encoding="unicode")


# ─── XML conversions ──────────────────────────────────────────────────────────

def xml_to_json(data: str) -> str:
    root = etree.fromstring(data.encode())
    records = []
    for item in root:
        record = {child.tag: child.text for child in item}
        records.append(record)
    return orjson.dumps(records).decode()


def xml_to_csv(data: str) -> str:
    json_str = xml_to_json(data)
    return json_to_csv(json_str)


# ─── YAML conversions ─────────────────────────────────────────────────────────

def yaml_to_json(data: str) -> str:
    yaml = YAML()
    parsed = yaml.load(data)
    return orjson.dumps(parsed).decode()


# ─── TOML conversions ─────────────────────────────────────────────────────────

def toml_to_json(data: str) -> str:
    parsed = tomllib.loads(data)
    return orjson.dumps(parsed).decode()
