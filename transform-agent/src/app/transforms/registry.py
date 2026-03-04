"""
Transform registry — maps (src_format, tgt_format) tuples to handler callables.
"""

from typing import Callable
from . import tabular, markup, documents, encoding

# ─── Conversion matrix ────────────────────────────────────────────────────────

REGISTRY: dict[tuple[str, str], Callable[[str], str]] = {
    # JSON
    ("json", "csv"):       tabular.json_to_csv,
    ("json", "xml"):       tabular.json_to_xml,
    ("json", "yaml"):      tabular.json_to_yaml,
    ("json", "toml"):      tabular.json_to_toml,
    # CSV
    ("csv", "json"):       tabular.csv_to_json,
    ("csv", "xml"):        tabular.csv_to_xml,
    # XML
    ("xml", "json"):       tabular.xml_to_json,
    ("xml", "csv"):        tabular.xml_to_csv,
    # YAML
    ("yaml", "json"):      tabular.yaml_to_json,
    # TOML
    ("toml", "json"):      tabular.toml_to_json,
    # HTML
    ("html", "markdown"):  markup.html_to_markdown,
    ("html", "text"):      markup.html_to_text,
    # Markdown
    ("markdown", "html"):  markup.markdown_to_html,
    # Text
    ("text", "html"):      markup.text_to_html,
    # Documents (input is base64-encoded bytes)
    ("pdf", "text"):       documents.pdf_to_text,
    ("pdf", "json"):       documents.pdf_to_json,
    ("xlsx", "csv"):       documents.xlsx_to_csv,
    ("xlsx", "json"):      documents.xlsx_to_json,
    ("docx", "text"):      documents.docx_to_text,
    ("docx", "markdown"):  documents.docx_to_markdown,
    # Encoding
    ("*", "base64"):       encoding.to_base64,
    ("base64", "*"):       encoding.from_base64,
    ("*", "hex"):          encoding.to_hex,
    ("hex", "*"):          encoding.from_hex,
    ("*", "url"):          encoding.to_url_encoded,
    ("url", "*"):          encoding.from_url_encoded,
}

# ─── Format categories ────────────────────────────────────────────────────────

TEXT_FORMATS = {"json", "csv", "xml", "yaml", "toml", "html", "markdown", "text"}
DOCUMENT_FORMATS = {"pdf", "xlsx", "docx"}
ENCODING_FORMATS = {"base64", "url", "hex"}


def get_handler(src: str, tgt: str) -> Callable[[str], str] | None:
    """Return the handler for (src, tgt), resolving wildcard entries."""
    # exact match first
    handler = REGISTRY.get((src, tgt))
    if handler:
        return handler
    # wildcard source
    handler = REGISTRY.get(("*", tgt))
    if handler:
        return handler
    # wildcard target
    handler = REGISTRY.get((src, "*"))
    if handler:
        return handler
    return None


def get_price(src: str, tgt: str) -> float:
    """Return the price in USDC for a conversion."""
    if src in DOCUMENT_FORMATS or tgt in DOCUMENT_FORMATS:
        return 0.005
    if src in TEXT_FORMATS or tgt in TEXT_FORMATS:
        return 0.001
    if src in ENCODING_FORMATS or tgt in ENCODING_FORMATS:
        return 0.001
    return 0.001


def list_capabilities() -> list[dict]:
    """Return all supported conversions with pricing info."""
    caps = []
    for (src, tgt) in REGISTRY:
        if src == "*" or tgt == "*":
            continue
        if src in DOCUMENT_FORMATS or tgt in DOCUMENT_FORMATS:
            category = "document"
        elif src in ENCODING_FORMATS or tgt in ENCODING_FORMATS:
            category = "encoding"
        else:
            category = "text"
        caps.append({
            "source_format": src,
            "target_format": tgt,
            "price_usdc": get_price(src, tgt),
            "category": category,
        })
    # add wildcard encoding descriptions
    for enc in ENCODING_FORMATS:
        caps.append({
            "source_format": "any",
            "target_format": enc,
            "price_usdc": 0.001,
            "category": "encoding",
        })
        caps.append({
            "source_format": enc,
            "target_format": "any",
            "price_usdc": 0.001,
            "category": "encoding",
        })
    return caps
