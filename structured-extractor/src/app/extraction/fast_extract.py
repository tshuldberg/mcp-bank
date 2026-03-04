"""
Fast/heuristic extraction — tries structured data sources before invoking LLM.
Order: JSON-LD → OpenGraph → Microdata → CSS heuristics.
Returns (data, confidence, method) tuple.
"""

from __future__ import annotations

import re
from typing import Any

# CSS selector patterns for common schema field names
_CSS_PATTERNS: dict[str, list[str]] = {
    "title": ["h1", ".title", ".product-title", ".article-title", "[itemprop='name']", "title"],
    "name": ["h1", ".name", ".product-name", "[itemprop='name']"],
    "price": [
        ".price", "#price", "[data-price]", "[itemprop='price']",
        ".product-price", ".offer-price", "span.amount",
    ],
    "description": [
        ".description", "[itemprop='description']", ".product-description",
        ".summary", "meta[name='description']", "p.description",
    ],
    "author": [".author", "[itemprop='author']", ".byline", "meta[name='author']", "[rel='author']"],
    "date": [
        "[itemprop='datePublished']", ".published-date", ".date", "time[datetime]",
        "meta[property='article:published_time']",
    ],
    "image": ["[itemprop='image']", ".product-image img", "meta[property='og:image']", "img.hero"],
    "currency": ["[itemprop='priceCurrency']", ".currency", "[data-currency]"],
    "in_stock": ["[itemprop='availability']", ".availability", ".stock-status"],
    "rating": ["[itemprop='ratingValue']", ".rating", ".stars", "[data-rating]"],
    "brand": ["[itemprop='brand']", ".brand", ".manufacturer", "[data-brand]"],
    "sku": ["[itemprop='sku']", ".sku", "#sku", "[data-sku]"],
    "url": ["[itemprop='url']", "link[rel='canonical']", "meta[property='og:url']"],
    "text_content": ["article", "main", ".content", ".article-body", ".post-body"],
    "published_date": [
        "[itemprop='datePublished']", "time[datetime]",
        "meta[property='article:published_time']", ".date",
    ],
}


def _get_schema_required(schema: dict) -> list[str]:
    return schema.get("required", [])


def _get_schema_fields(schema: dict) -> list[str]:
    return list(schema.get("properties", {}).keys())


def _compute_confidence(data: dict, schema: dict) -> float:
    """Confidence = matched required fields / total required fields (min 0.0)."""
    required = _get_schema_required(schema)
    if not required:
        fields = _get_schema_fields(schema)
        if not fields:
            return 0.5
        matched = sum(1 for f in fields if data.get(f) is not None)
        return matched / len(fields)
    matched = sum(1 for f in required if data.get(f) is not None)
    return matched / len(required)


def extract_json_ld(html: str, schema: dict) -> dict | None:
    """
    Parse JSON-LD blocks and map fields to the caller's schema.
    Returns None if no useful JSON-LD found.
    """
    try:
        import extruct  # type: ignore[import]
        from w3lib.html import get_base_url  # type: ignore[import]

        base_url = get_base_url(html)
        data = extruct.extract(html, base_url=base_url, syntaxes=["json-ld"], uniform=True)
        items = data.get("json-ld", [])
    except Exception:
        return None

    if not items:
        return None

    fields = _get_schema_fields(schema)
    result: dict[str, Any] = {}

    for item in items:
        _map_fields(item, fields, result)
        if result:
            break

    return result if result else None


def extract_opengraph(html: str, schema: dict) -> dict | None:
    """
    Parse Open Graph and standard meta tags, map to schema fields.
    """
    try:
        import extruct  # type: ignore[import]
        from w3lib.html import get_base_url  # type: ignore[import]

        base_url = get_base_url(html)
        data = extruct.extract(html, base_url=base_url, syntaxes=["opengraph"], uniform=True)
        items = data.get("opengraph", [])
    except Exception:
        return None

    if not items:
        return None

    fields = _get_schema_fields(schema)
    result: dict[str, Any] = {}

    for item in items:
        _map_fields(item, fields, result)

    return result if result else None


def extract_microdata(html: str, schema: dict) -> dict | None:
    """
    Parse microdata (itemprop/itemscope), map to schema fields.
    """
    try:
        import extruct  # type: ignore[import]
        from w3lib.html import get_base_url  # type: ignore[import]

        base_url = get_base_url(html)
        data = extruct.extract(html, base_url=base_url, syntaxes=["microdata"], uniform=True)
        items = data.get("microdata", [])
    except Exception:
        return None

    if not items:
        return None

    fields = _get_schema_fields(schema)
    result: dict[str, Any] = {}

    for item in items:
        props = item.get("properties", {})
        _map_fields(props, fields, result)
        if result:
            break

    return result if result else None


def extract_css_heuristics(html: str, schema: dict) -> dict | None:
    """
    Try common CSS selector patterns for each schema field.
    Uses BeautifulSoup for parsing.
    """
    try:
        from bs4 import BeautifulSoup
    except Exception:
        return None

    soup = BeautifulSoup(html, "lxml")
    fields = _get_schema_fields(schema)
    result: dict[str, Any] = {}

    for field in fields:
        selectors = _CSS_PATTERNS.get(field, [])
        # Also try generic patterns using the field name itself
        selectors = selectors + [
            f"[class*='{field}']",
            f"[id*='{field}']",
            f"[data-{field}]",
            f"[itemprop='{field}']",
        ]

        for selector in selectors:
            try:
                el = soup.select_one(selector)
                if el is None:
                    continue

                # For meta tags, prefer content attribute
                value = el.get("content") or el.get("datetime") or el.get("href")
                if value is None:
                    value = el.get_text(strip=True)

                if value:
                    result[field] = value
                    break
            except Exception:
                continue

    return result if result else None


def fast_extract(html: str, schema: dict) -> tuple[dict | None, float, str]:
    """
    Try all fast extraction methods in priority order.

    Returns:
        (data, confidence, method) where method is one of:
        'json_ld', 'opengraph', 'microdata', 'css_heuristic', or 'none'
    """
    # 1. JSON-LD (highest confidence — structured data embedded by the site)
    data = extract_json_ld(html, schema)
    if data:
        conf = _compute_confidence(data, schema)
        if conf > 0:
            return data, min(conf + 0.1, 1.0), "json_ld"  # bonus for structured source

    # 2. OpenGraph meta tags
    data = extract_opengraph(html, schema)
    if data:
        conf = _compute_confidence(data, schema)
        if conf > 0:
            return data, conf, "opengraph"

    # 3. Microdata
    data = extract_microdata(html, schema)
    if data:
        conf = _compute_confidence(data, schema)
        if conf > 0:
            return data, conf, "microdata"

    # 4. CSS heuristics
    data = extract_css_heuristics(html, schema)
    if data:
        conf = _compute_confidence(data, schema)
        if conf > 0:
            return data, conf, "css_heuristic"

    return None, 0.0, "none"


def _map_fields(source: dict, fields: list[str], target: dict) -> None:
    """
    Map fields from a source dict to target, using case-insensitive fuzzy matching.
    Mutates target in place.
    """
    source_lower = {k.lower(): v for k, v in source.items()}
    for field in fields:
        if field in target:
            continue
        # Try exact match, then lowercase, then partial match
        val = source.get(field) or source_lower.get(field.lower())
        if val is None:
            # Try partial key match (e.g. "productName" → "name")
            for k, v in source_lower.items():
                if field.lower() in k or k in field.lower():
                    val = v
                    break
        if val is not None and val != "":
            # Flatten lists to first element for simple fields
            if isinstance(val, list) and len(val) == 1:
                val = val[0]
            target[field] = val
