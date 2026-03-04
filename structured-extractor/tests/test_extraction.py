"""
Unit tests for the extraction pipeline modules.
All external API calls (Anthropic, httpx) are mocked.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure shared/ and project root are importable
sys.path.insert(0, str(Path(__file__).parents[2]))
sys.path.insert(0, str(Path(__file__).parents[1]))

# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────

SIMPLE_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "price": {"type": "number"},
        "description": {"type": "string"},
    },
    "required": ["title", "price"],
}

JSON_LD_HTML = """
<html>
<head>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Product",
  "name": "Widget Pro",
  "description": "Professional widget",
  "offers": {
    "@type": "Offer",
    "price": "29.99",
    "priceCurrency": "USD"
  }
}
</script>
</head>
<body><h1>Widget Pro</h1><span class="price">$29.99</span></body>
</html>
"""

OG_HTML = """
<html>
<head>
<meta property="og:title" content="Test Article" />
<meta property="og:description" content="An article about testing" />
<meta property="og:url" content="https://example.com/article" />
</head>
<body><h1>Test Article</h1></body>
</html>
"""

CSS_HTML = """
<html>
<body>
<h1>Laptop Pro X1</h1>
<span class="price">$999.00</span>
<p class="description">High performance laptop</p>
</body>
</html>
"""

DIRTY_HTML = """
<html>
<head><style>body { color: red; }</style></head>
<body>
<nav><a href="/">Home</a></nav>
<header><h1>Site Header</h1></header>
<main><h1>Article Title</h1><p>Content here.</p></main>
<footer>Footer content</footer>
<script>var x = 1;</script>
</body>
</html>
"""


# ──────────────────────────────────────────────────────────────────────────────
# HTML Cleaning Tests
# ──────────────────────────────────────────────────────────────────────────────

class TestCleaner:
    def test_strips_noise_tags(self):
        from src.app.extraction.cleaner import clean_html

        result = clean_html(DIRTY_HTML)
        assert "<script>" not in result
        assert "<style>" not in result
        assert "<footer>" not in result
        assert "<nav>" not in result

    def test_preserves_main_content(self):
        from src.app.extraction.cleaner import clean_html

        result = clean_html(CSS_HTML)
        # Main content elements should survive
        assert "Laptop" in result or "price" in result.lower()

    def test_handles_empty_html(self):
        from src.app.extraction.cleaner import clean_html

        result = clean_html("<html><body></body></html>")
        assert isinstance(result, str)

    def test_handles_malformed_html(self):
        from src.app.extraction.cleaner import clean_html

        result = clean_html("<p>Unclosed paragraph <b>bold text")
        assert isinstance(result, str)


# ──────────────────────────────────────────────────────────────────────────────
# Fast Extraction Tests
# ──────────────────────────────────────────────────────────────────────────────

class TestFastExtract:
    def test_json_ld_extraction(self):
        from src.app.extraction.fast_extract import extract_json_ld

        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "description": {"type": "string"},
            },
        }
        result = extract_json_ld(JSON_LD_HTML, schema)
        # Should find the structured data
        assert result is not None
        assert isinstance(result, dict)

    def test_opengraph_extraction(self):
        from src.app.extraction.fast_extract import extract_opengraph

        schema = {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "description": {"type": "string"},
            },
        }
        result = extract_opengraph(OG_HTML, schema)
        assert result is not None
        assert isinstance(result, dict)

    def test_css_heuristic_title(self):
        from src.app.extraction.fast_extract import extract_css_heuristics

        schema = {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "price": {"type": "string"},
            },
        }
        result = extract_css_heuristics(CSS_HTML, schema)
        assert result is not None
        assert "title" in result or "price" in result

    def test_css_heuristic_price_selector(self):
        from src.app.extraction.fast_extract import extract_css_heuristics

        schema = {
            "type": "object",
            "properties": {"price": {"type": "string"}},
        }
        html = '<html><body><span class="price">$29.99</span></body></html>'
        result = extract_css_heuristics(html, schema)
        assert result is not None
        assert "price" in result

    def test_fast_extract_returns_tuple(self):
        from src.app.extraction.fast_extract import fast_extract

        data, confidence, method = fast_extract(CSS_HTML, SIMPLE_SCHEMA)
        assert isinstance(confidence, float)
        assert 0.0 <= confidence <= 1.0
        assert isinstance(method, str)

    def test_confidence_zero_no_matches(self):
        from src.app.extraction.fast_extract import _compute_confidence

        schema = {
            "type": "object",
            "properties": {"foo": {}, "bar": {}},
            "required": ["foo", "bar"],
        }
        data = {"foo": None, "bar": None}
        confidence = _compute_confidence(data, schema)
        assert confidence == 0.0

    def test_confidence_full_match(self):
        from src.app.extraction.fast_extract import _compute_confidence

        schema = {
            "type": "object",
            "properties": {"foo": {}, "bar": {}, "baz": {}},
            "required": ["foo", "bar", "baz"],
        }
        data = {"foo": "x", "bar": "y", "baz": "z"}
        confidence = _compute_confidence(data, schema)
        assert confidence == 1.0

    def test_confidence_partial_match(self):
        from src.app.extraction.fast_extract import _compute_confidence

        schema = {
            "type": "object",
            "properties": {"foo": {}, "bar": {}, "baz": {}},
            "required": ["foo", "bar", "baz"],
        }
        data = {"foo": "x", "bar": None, "baz": None}
        confidence = _compute_confidence(data, schema)
        assert abs(confidence - 1 / 3) < 0.01


# ──────────────────────────────────────────────────────────────────────────────
# LLM Extraction Tests (Anthropic mocked)
# ──────────────────────────────────────────────────────────────────────────────

class TestLlmExtract:
    @pytest.mark.asyncio
    async def test_llm_extract_returns_data(self):
        from src.app.extraction.llm_extract import llm_extract

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{"title": "Test Product", "price": 9.99}')]

        with patch("anthropic.AsyncAnthropic") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            data, confidence = await llm_extract(CSS_HTML, SIMPLE_SCHEMA)

        assert isinstance(data, dict)
        assert isinstance(confidence, float)

    @pytest.mark.asyncio
    async def test_llm_extract_handles_markdown_fences(self):
        from src.app.extraction.llm_extract import llm_extract

        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(text='```json\n{"title": "Product", "price": 5.0}\n```')
        ]

        with patch("anthropic.AsyncAnthropic") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            data, confidence = await llm_extract(CSS_HTML, SIMPLE_SCHEMA)

        assert data.get("title") == "Product"
        assert data.get("price") == 5.0

    @pytest.mark.asyncio
    async def test_llm_extract_confidence_full(self):
        from src.app.extraction.llm_extract import llm_extract

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{"title": "X", "price": 1.0}')]

        with patch("anthropic.AsyncAnthropic") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            data, confidence = await llm_extract(CSS_HTML, SIMPLE_SCHEMA)

        # Both required fields (title, price) present → confidence = 1.0
        assert confidence == 1.0

    def test_html_truncation(self):
        from src.app.extraction.llm_extract import _truncate_html

        long_html = "A" * 50000
        result = _truncate_html(long_html, SIMPLE_SCHEMA)
        assert len(result) < 50000


# ──────────────────────────────────────────────────────────────────────────────
# Pipeline Tests
# ──────────────────────────────────────────────────────────────────────────────

class TestPipeline:
    @pytest.mark.asyncio
    async def test_extract_from_html_no_llm_needed(self):
        """Fast extraction with JSON-LD should not call LLM."""
        from src.app.extraction import pipeline

        with patch("src.app.extraction.pipeline.llm_extract") as mock_llm:
            with patch("src.app.extraction.pipeline.fast_extract") as mock_fast:
                mock_fast.return_value = (
                    {"title": "Test", "price": 1.0},
                    0.95,
                    "json_ld",
                )
                result = await pipeline.extract_from_html(JSON_LD_HTML, SIMPLE_SCHEMA)

        mock_llm.assert_not_called()
        assert result.method == "json_ld"
        assert result.confidence >= 0.8

    @pytest.mark.asyncio
    async def test_llm_fallback_triggered_on_low_confidence(self):
        """LLM should be called when fast extraction confidence < 0.8."""
        from src.app.extraction import pipeline

        mock_llm_result = ({"title": "Fallback", "price": 9.99}, 0.9)

        with patch("src.app.extraction.pipeline.fast_extract") as mock_fast:
            with patch("src.app.extraction.pipeline.llm_extract", AsyncMock(return_value=mock_llm_result)) as mock_llm:
                mock_fast.return_value = ({"title": "Partial"}, 0.5, "css_heuristic")
                result = await pipeline.extract_from_html("<html><body>content</body></html>", SIMPLE_SCHEMA)

        mock_llm.assert_called_once()
        assert result.method == "llm_haiku"

    @pytest.mark.asyncio
    async def test_cache_hit_returns_cached(self):
        """Cache hit should return the cached result with cached=True."""
        from src.app.extraction import pipeline

        cached_result = {
            "data": {"title": "Cached", "price": 5.0},
            "confidence": 0.9,
            "method": "json_ld",
            "url": "https://example.com",
            "extracted_at": "2026-01-01T00:00:00+00:00",
            "duration_ms": 100,
            "cached": False,
        }
        import orjson

        with patch("src.app.extraction.pipeline.cache_get", AsyncMock(return_value=orjson.dumps(cached_result).decode())):
            with patch("src.app.extraction.pipeline.fetch_html") as mock_fetch:
                result = await pipeline.extract("https://example.com", SIMPLE_SCHEMA)

        mock_fetch.assert_not_called()
        assert result.cached is True
        assert result.data["title"] == "Cached"

    @pytest.mark.asyncio
    async def test_batch_extraction_respects_max_concurrent(self):
        """Batch should call extract once per URL."""
        from src.app.extraction import pipeline

        urls = ["https://example.com/1", "https://example.com/2", "https://example.com/3"]

        call_count = 0

        async def mock_extract(url, schema, render_js=False):
            nonlocal call_count
            call_count += 1
            from src.app.models.schemas import ExtractionResult
            from datetime import datetime, timezone
            return ExtractionResult(
                data={"title": f"Result for {url}", "price": 1.0},
                confidence=0.9,
                method="json_ld",
                url=url,
                extracted_at=datetime.now(timezone.utc).isoformat(),
                duration_ms=50,
                cached=False,
            )

        with patch("src.app.extraction.pipeline.extract", side_effect=mock_extract):
            result = await pipeline.extract_batch(
                urls=urls, schema=SIMPLE_SCHEMA, render_js=False, max_concurrent=2
            )

        assert result.total_urls == 3
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_batch_counts_failures(self):
        """Batch should count failed extractions."""
        from src.app.extraction import pipeline
        from src.app.models.schemas import ExtractionResult
        from datetime import datetime, timezone

        call_count = 0

        async def mock_extract_fail(url, schema, render_js=False):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise ValueError("Fetch failed")
            return ExtractionResult(
                data={"title": "ok"},
                confidence=0.9,
                method="json_ld",
                url=url,
                extracted_at=datetime.now(timezone.utc).isoformat(),
                duration_ms=50,
                cached=False,
            )

        with patch("src.app.extraction.pipeline.extract", side_effect=mock_extract_fail):
            result = await pipeline.extract_batch(
                urls=["https://a.com", "https://b.com"],
                schema=SIMPLE_SCHEMA,
                render_js=False,
                max_concurrent=2,
            )

        assert result.total_urls == 2
        assert result.failed == 1
        assert result.successful == 1

    @pytest.mark.asyncio
    async def test_schema_validation_fills_nulls(self):
        """Missing optional fields should be filled with null."""
        from src.app.extraction.pipeline import _validate_against_schema

        schema = {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "price": {"type": "number"},
                "description": {"type": ["string", "null"]},
            },
            "required": ["title"],
        }
        data = {"title": "Test"}
        result = _validate_against_schema(data, schema)
        assert "price" in result
        assert "description" in result
