"""Indian regulatory filing connector using NSE and BSE public APIs.

Provides corporate filing data and risk scoring for Indian companies
listed on NSE (.NS) and BSE (.BO). Equivalent of SEC Edgar for India.
Uses public endpoints — no API key required.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx
from cachetools import TTLCache

logger = logging.getLogger(__name__)

# Risk keywords to scan in Indian corporate announcements
RISK_KEYWORDS_IN: dict[str, list[str]] = {
    "going_concern": ["going concern", "ability to continue"],
    "restatement": ["restatement", "restated", "revision of accounts"],
    "sebi_investigation": ["sebi", "investigation", "show cause", "penalty"],
    "material_weakness": ["material weakness", "qualification", "qualified opinion"],
    "delisting_risk": ["delisting", "compulsory delisting"],
    "insider_trading": ["insider trading", "unpublished price sensitive"],
    "related_party": ["related party transaction"],
}


def _extract_nse_symbol(ticker: str) -> str:
    """Extract NSE symbol from ticker (e.g. 'RELIANCE.NS' -> 'RELIANCE')."""
    return ticker.replace(".NS", "").replace(".BO", "").upper()


class IndiaComplianceConnector:
    """Fetch Indian corporate filings from NSE/BSE public endpoints."""

    NSE_ANNOUNCEMENTS_URL = "https://www.nseindia.com/api/corporate-announcements"
    BSE_ANNOUNCEMENTS_URL = "https://api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w"

    def __init__(self) -> None:
        self.cache: TTLCache = TTLCache(maxsize=64, ttl=300)
        self.client = httpx.AsyncClient(
            timeout=15.0,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0"
                ),
                "Accept": "application/json",
                "Accept-Language": "en-US,en;q=0.9",
            },
            follow_redirects=True,
        )

    async def _fetch_nse_announcements(self, symbol: str) -> list[dict]:
        """Fetch corporate announcements from NSE. Returns [] on error."""
        cache_key = f"nse_ann_{symbol}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            # NSE requires a session cookie — first hit the main page
            await self.client.get("https://www.nseindia.com", timeout=5.0)

            params = {"index": "equities", "symbol": symbol}
            response = await self.client.get(self.NSE_ANNOUNCEMENTS_URL, params=params)
            if response.status_code != 200:
                return []

            data = response.json()
            announcements = []
            for item in data[:20]:  # Last 20 announcements
                announcements.append(
                    {
                        "filing_type": item.get("desc", "Corporate Announcement"),
                        "filed_date": item.get("an_dt", ""),
                        "description": item.get("attchmntText", item.get("desc", "")),
                        "url": item.get("attchmntFile", ""),
                        "subject": item.get("smIndustry", ""),
                    }
                )

            self.cache[cache_key] = announcements
            return announcements
        except Exception as exc:
            logger.warning("NSE announcements error for %s: %s", symbol, exc)
            return []

    async def _fetch_via_yfinance(self, ticker: str) -> list[dict]:
        """Fallback: use yfinance to get basic company info and news for risk flags."""
        cache_key = f"yf_compliance_{ticker}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            import yfinance as yf

            stock = yf.Ticker(ticker)
            info = stock.info or {}

            filings = []

            # Check for recent corporate actions from yfinance
            actions = stock.actions
            if actions is not None and not actions.empty:
                for date_idx in actions.index[-5:]:
                    filings.append(
                        {
                            "filing_type": "Corporate Action",
                            "filed_date": date_idx.strftime("%Y-%m-%d"),
                            "description": (
                                f"Dividends: {actions.loc[date_idx].get('Dividends', 0)}, "
                                f"Stock Splits: {actions.loc[date_idx].get('Stock Splits', 0)}"
                            ),
                            "url": "",
                        }
                    )

            # Use basic info as a filing proxy
            audit_risk = info.get("auditRisk")
            board_risk = info.get("boardRisk")
            overall_risk = info.get("overallRisk")

            if audit_risk is not None or board_risk is not None:
                filings.insert(
                    0,
                    {
                        "filing_type": "Governance Report",
                        "filed_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                        "description": (
                            f"Audit risk: {audit_risk}, Board risk: {board_risk}, "
                            f"Overall risk: {overall_risk}. "
                            f"Sector: {info.get('sector', 'N/A')}. "
                            f"Market cap: {info.get('marketCap', 'N/A')}."
                        ),
                        "url": "",
                    },
                )

            self.cache[cache_key] = filings
            return filings
        except Exception as exc:
            logger.warning("yfinance compliance fallback error for %s: %s", ticker, exc)
            return []

    async def get_filings(self, ticker: str, count: int = 10) -> list[dict]:
        """Fetch recent corporate filings for an Indian ticker."""
        symbol = _extract_nse_symbol(ticker)

        # Try NSE first
        filings = await self._fetch_nse_announcements(symbol)

        # Fallback to yfinance-based data
        if not filings:
            filings = await self._fetch_via_yfinance(ticker)

        return filings[:count]

    async def score_risk(self, ticker: str) -> dict:
        """Analyze Indian filings for regulatory risk. Returns {} on total failure."""
        cache_key = f"india_risk_{ticker}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            filings = await self.get_filings(ticker, count=15)

            if not filings:
                # No filing data — return moderate risk due to lack of information
                return {
                    "latest_filing_type": "Unknown",
                    "days_since_filing": 0,
                    "risk_flags": [],
                    "risk_score": 0.3,
                }

            latest = filings[0]
            latest_filing_type = latest.get("filing_type", "Unknown")

            # Calculate days since most recent filing
            days_since = 0
            try:
                date_str = latest.get("filed_date", "")
                if date_str:
                    # Handle multiple date formats
                    for fmt in ("%Y-%m-%d", "%d-%b-%Y", "%d/%m/%Y", "%d-%m-%Y"):
                        try:
                            filed_dt = datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)
                            days_since = (datetime.now(timezone.utc) - filed_dt).days
                            break
                        except ValueError:
                            continue
            except Exception:
                pass

            # Detect risk flags
            risk_flags: list[str] = []
            all_text = " ".join(f.get("description", "").lower() for f in filings)

            for flag, keywords in RISK_KEYWORDS_IN.items():
                if any(kw in all_text for kw in keywords):
                    risk_flags.append(flag)

            # Check for stale filings (Indian quarterly results due within 45 days)
            if days_since > 120:
                risk_flags.append("late_filing")

            # Calculate risk score
            risk_score = 0.0
            risk_score += len(risk_flags) * 0.1
            if "going_concern" in risk_flags:
                risk_score += 0.5
            if "restatement" in risk_flags:
                risk_score += 0.5
            if "sebi_investigation" in risk_flags:
                risk_score += 0.3
            if days_since > 180:
                risk_score += 0.2

            risk_score = max(0.0, min(1.0, risk_score))

            result = {
                "latest_filing_type": latest_filing_type,
                "days_since_filing": days_since,
                "risk_flags": sorted(risk_flags),
                "risk_score": risk_score,
            }

            self.cache[cache_key] = result
            return result
        except Exception:
            return {}

    async def close(self) -> None:
        """Close the underlying httpx client."""
        await self.client.aclose()


india_compliance = IndiaComplianceConnector()
