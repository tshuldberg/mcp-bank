"""
HTML content cleaning — strips noise (nav, ads, scripts) to leave main content.
Uses readability-lxml (Mozilla Reader View algorithm) as primary path,
with BeautifulSoup fallback for pages readability can't handle.
"""

from __future__ import annotations

_REMOVE_TAGS = {"script", "style", "nav", "footer", "header", "aside", "form", "noscript"}


def clean_html(raw_html: str) -> str:
    """
    Extract and clean main content from raw HTML.

    Uses readability-lxml to identify the main article content (like Mozilla
    Reader View), then strips remaining noise tags. Falls back to a manual
    BeautifulSoup strip if readability fails.

    Args:
        raw_html: Raw HTML string from the fetcher.

    Returns:
        Cleaned HTML string suitable for extraction.
    """
    try:
        from readability import Document  # type: ignore[import]

        doc = Document(raw_html)
        cleaned = doc.summary(html_partial=True)
        return _strip_tags(cleaned)
    except Exception:
        pass

    # Fallback: manual tag stripping via BeautifulSoup
    return _strip_tags(raw_html)


def _strip_tags(html: str) -> str:
    """Strip noise tags from HTML using BeautifulSoup."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "lxml")
    for tag in soup.find_all(_REMOVE_TAGS):
        tag.decompose()
    return str(soup)
