"""
Async HTML fetcher for the Structured Extractor.
Handles redirects, errors, and timeouts gracefully.
"""

from __future__ import annotations

import httpx

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; mcp-bank-extractor/1.0; "
        "+https://github.com/tshuldberg/mcp-bank)"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

_TIMEOUT = 15.0


async def fetch_html(url: str, render_js: bool = False) -> str:
    """
    Fetch HTML content from a URL.

    Args:
        url: The URL to fetch.
        render_js: If True, JS rendering would be used (not yet available).

    Returns:
        Raw HTML string.

    Raises:
        ValueError: For invalid URLs or HTTP errors.
        NotImplementedError: If render_js=True (Playwright not yet integrated).
    """
    if render_js:
        # TODO: Playwright integration — self-host on Fly.io with persistent browser pool.
        # For now, return a clear error rather than silently falling back.
        raise NotImplementedError(
            "JS rendering (render_js=True) is not yet available. "
            "Playwright support is planned for a future release. "
            "Use render_js=False for HTML-only extraction."
        )

    async with httpx.AsyncClient(
        headers=_HEADERS,
        follow_redirects=True,
        timeout=_TIMEOUT,
    ) as client:
        try:
            response = await client.get(url)
        except httpx.TimeoutException:
            raise ValueError(f"Request timed out after {_TIMEOUT}s: {url}")
        except httpx.RequestError as e:
            raise ValueError(f"Failed to fetch {url}: {e}")

        if response.status_code == 404:
            raise ValueError(f"URL not found (404): {url}")
        if response.status_code == 403:
            raise ValueError(f"Access forbidden (403): {url}")
        if response.status_code >= 400:
            raise ValueError(f"HTTP {response.status_code} error fetching: {url}")

        return response.text
