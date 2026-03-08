"""SEC Edgar async wrapper with risk scoring and TTL caching.

Provides SEC filing data and regulatory risk analysis for the ComplianceChecker agent.
"""

from __future__ import annotations

from datetime import datetime, timezone

import httpx
from cachetools import TTLCache

from config.settings import Settings, get_settings

# Risk flag keywords to scan for in filing descriptions
RISK_KEYWORDS: dict[str, list[str]] = {
    "going_concern": ["going concern"],
    "restatement": ["restatement"],
    "sec_investigation": ["sec investigation", "investigation"],
    "material_weakness": ["material weakness"],
    "delisting_risk": ["delisting"],
}


class SecConnector:
    """Async SEC EDGAR wrapper with risk scoring and 5-min TTL cache."""

    SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
    SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"

    def __init__(self, settings: Settings | None = None) -> None:
        _settings = settings or get_settings()
        self.user_agent = "EquityIQ nishantgaurav23@gmail.com"
        self.cache: TTLCache = TTLCache(maxsize=64, ttl=300)
        self.client = httpx.AsyncClient(
            timeout=10.0,
            headers={"User-Agent": self.user_agent},
        )

    async def get_company_cik(self, ticker: str) -> str | None:
        """Resolve a ticker symbol to SEC CIK number. Returns None on error."""
        cache_key = f"cik_{ticker.upper()}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            response = await self.client.get(self.SEC_TICKERS_URL)
            if response.status_code != 200:
                return None

            data = response.json()
            ticker_upper = ticker.upper()

            for entry in data.values():
                if entry.get("ticker", "").upper() == ticker_upper:
                    cik = str(entry["cik_str"])
                    self.cache[cache_key] = cik
                    return cik

            return None
        except Exception:
            return None

    async def get_sec_filings(
        self, ticker: str, filing_type: str | None = None, count: int = 5
    ) -> list[dict]:
        """Fetch recent SEC filings for a ticker. Returns [] on error."""
        cache_key = f"filings_{ticker.upper()}_{filing_type}_{count}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            cik = await self.get_company_cik(ticker)
            if cik is None:
                return []

            # Pad CIK to 10 digits as required by SEC API
            cik_padded = cik.zfill(10)
            url = self.SEC_SUBMISSIONS_URL.format(cik=cik_padded)

            response = await self.client.get(url)
            if response.status_code != 200:
                return []

            data = response.json()
            recent = data.get("filings", {}).get("recent", {})

            forms = recent.get("form", [])
            dates = recent.get("filingDate", [])
            accessions = recent.get("accessionNumber", [])
            docs = recent.get("primaryDocument", [])
            descriptions = recent.get("primaryDocDescription", [])

            filings = []
            for i in range(len(forms)):
                if filing_type and forms[i] != filing_type:
                    continue

                accession_clean = accessions[i].replace("-", "") if i < len(accessions) else ""
                doc_name = docs[i] if i < len(docs) else ""
                filing_url = (
                    f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_clean}/{doc_name}"
                )

                filings.append(
                    {
                        "filing_type": forms[i],
                        "filed_date": dates[i] if i < len(dates) else "",
                        "description": descriptions[i] if i < len(descriptions) else "",
                        "url": filing_url,
                    }
                )

                if len(filings) >= count:
                    break

            self.cache[cache_key] = filings
            return filings
        except Exception:
            return []

    async def score_risk(self, ticker: str) -> dict:
        """Analyze SEC filings for regulatory risk. Returns {} on total failure."""
        cache_key = f"risk_{ticker.upper()}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            filings = await self.get_sec_filings(ticker, count=10)

            if not filings:
                return {}

            latest = filings[0]
            latest_filing_type = latest["filing_type"]

            # Calculate days since most recent filing
            try:
                filed_dt = datetime.strptime(latest["filed_date"], "%Y-%m-%d").replace(
                    tzinfo=timezone.utc
                )
                days_since = (datetime.now(timezone.utc) - filed_dt).days
            except (ValueError, KeyError):
                days_since = 0

            # Detect risk flags from all filing descriptions
            risk_flags: list[str] = []
            all_descriptions = " ".join(
                f.get("description", "").lower() for f in filings
            )

            for flag, keywords in RISK_KEYWORDS.items():
                if any(kw in all_descriptions for kw in keywords):
                    risk_flags.append(flag)

            # Check for late filings
            if latest_filing_type == "10-Q" and days_since > 90:
                risk_flags.append("late_filing")
            elif latest_filing_type == "10-K" and days_since > 395:
                risk_flags.append("late_filing")
            elif days_since > 395:
                risk_flags.append("late_filing")

            # Calculate risk score
            risk_score = 0.0
            risk_score += len(risk_flags) * 0.1
            if "going_concern" in risk_flags:
                risk_score += 0.5
            if "restatement" in risk_flags:
                risk_score += 0.5
            if days_since > 180:
                risk_score += 0.2

            # Clamp to [0.0, 1.0]
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


sec = SecConnector()
