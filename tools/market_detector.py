"""Utility to detect which market a ticker belongs to.

Used by agents to route to the correct data source (US vs India).
"""

from __future__ import annotations


def is_indian_ticker(ticker: str) -> bool:
    """Return True if the ticker is an Indian stock (NSE or BSE)."""
    t = ticker.upper().strip()
    return t.endswith(".NS") or t.endswith(".BO")


def get_market(ticker: str) -> str:
    """Return market identifier: 'in' for India, 'us' for US/default."""
    return "in" if is_indian_ticker(ticker) else "us"


def get_company_name_for_search(ticker: str) -> str:
    """Strip exchange suffix for news search queries.

    e.g., 'RELIANCE.NS' -> 'RELIANCE', 'TCS.BO' -> 'TCS'
    """
    t = ticker.upper().strip()
    for suffix in (".NS", ".BO"):
        if t.endswith(suffix):
            return t[: -len(suffix)]
    return t
