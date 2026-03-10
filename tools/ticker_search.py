"""Ticker search/autocomplete via Polygon.io."""

from __future__ import annotations

import logging

import httpx
from cachetools import TTLCache

from config.settings import get_settings

logger = logging.getLogger(__name__)

# 1hr TTL cache, max 256 entries
_search_cache: TTLCache = TTLCache(maxsize=256, ttl=3600)


async def search_tickers(query: str, limit: int = 8) -> list[dict]:
    """Search for tickers matching query string.

    Uses Polygon.io's /v3/reference/tickers endpoint with search parameter.
    Returns list of {ticker, name, market, type, locale} dicts.
    Caches results for 1 hour. Returns empty list on any failure.
    """
    query = query.strip()
    if not query:
        return []

    cache_key = f"{query.lower()}:{limit}"
    if cache_key in _search_cache:
        return _search_cache[cache_key]

    try:
        settings = get_settings()
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://api.polygon.io/v3/reference/tickers",
                params={
                    "search": query,
                    "active": "true",
                    "market": "stocks",
                    "limit": limit,
                    "apiKey": settings.POLYGON_API_KEY,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        results = []
        for item in data.get("results", []):
            results.append(
                {
                    "ticker": item.get("ticker", ""),
                    "name": item.get("name", ""),
                    "market": item.get("market", ""),
                    "type": item.get("type", ""),
                    "locale": item.get("locale", ""),
                }
            )

        _search_cache[cache_key] = results
        return results
    except Exception:
        logger.warning("Ticker search failed for query: %s", query)
        return []
