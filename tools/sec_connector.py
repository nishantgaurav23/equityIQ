"""
What It Does:
    Fetches SEC filings from SEC Edgar for a given ticker and computes a regulatory risk score. Like
    news_connector.py, it both fetches AND processes - it scores risk based on what flags it finds in filings.

Why It's Needed:
    ComplianceChecker needs filing data + a risk score. SEC Edgar is free and the authoritative source for all public
    company filings.

How It Helps:

  - agents/compliance_checker.py calls get_filing_risk(ticker)
  - Returns ComplianceReport-ready fields: filing type, days since filing, risk flags, risk score

---
What to notice

  ┌─────────────────────────────────────┬────────────────────────────────────────────────────────────────────────────┐
  │               Pattern               │                                    Why                                     │
  ├─────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────┤
  │ User-Agent header in __init__       │ SEC blocks requests without it — set once, applied to every call           │
  ├─────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────┤
  │ str(cik).zfill(10)                  │ SEC CIK must be 10 digits with leading zeros                               │
  ├─────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────┤
  │ zip(forms, dates, accessions)       │ SEC returns 3 parallel lists — zip joins them row by row                   │
  ├─────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────┤
  │ break after adding flag             │ Once a flag is detected, no need to check remaining keywords for same flag │
  ├─────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────┤
  │ detect_risk_flags(str(most_recent)) │ Converts the filing dict to string for simple keyword scanning             │

"""
import os
import httpx
from datetime import datetime
from cachetools import TTLCache
from dotenv import load_dotenv

load_dotenv()

class SecConnector:
    """
    Async SEC Edgar wrapper with TTL caching and risk scoring.
    """
    def __init__(self):
        self.base_url = "https://data.sec.gov"
        self.cache = TTLCache(maxsize=64, ttl=3600)
        self.client = httpx.AsyncClient(
            timeout=10.0,
            headers={"User-Agent": "equityiq contact@equityiq.com"}
        )

        self.risk_keywords = {
            "going_concern":   ["going concern", "substantial doubt", "ability to continue"],
            "restatement":     ["restatement", "restated", "material weakness"],
            "investigation":   ["sec investigation", "doj probe", "under investigation"],
            "insider_selling": ["form 4", "disposed", "sold shares"],
            "late_filing":     ["nt 10-k", "nt 10-q", "notification of late filing"],
        }

    async def get_cik(self, ticker: str) -> str | None:
        """
        Converts a ticker symbol to SEC CIK number.
        CIK is required for all SEC Edgar API calls.
        Returns CIK string e.g. "0000320193" for AAPL, None on failure
        """
        cache_key = f"cik_{ticker}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        try:
            url = "https://www.sec.gov/files/company_tickers.json"
            response = await self.client.get(url)
            if response.status_code != 200:
                return None
            
            data = response.json()

            for entry in data.values():
                if entry.get("ticker", "").upper() == ticker.upper():
                    cik = str(entry["cik_str"]).zfill(10)
                    self.cache[cache_key] = cik
                    return cik

            return None

        except Exception:
            return None


    async def get_recent_filings(self, ticker: str) -> list[dict]:
        """
        Fetches 5 most recent SEC filings for a ticker.
        Filters for 10-K, 10-Q, and 8-K only.
        Returns list of dicts with form, filingDate, accessionNumber.
        Returns empty list of failure
        """
        cache_key = f"filings_{ticker}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            cik = await self.get_cik(ticker)
            if cik is None:
                return []

            url = f"{self.base_url}/submissions/CIK{cik}.json"
            response = await self.client.get(url)
            if response.status_code != 200:
                return []

            data = response.json()
            if "filings" not in data:
                return []

            recent = data["filings"].get("recent", {})
            forms = recent.get("form", [])
            dates = recent.get("filingDate", [])
            accessions = recent.get("accessionNumber", [])

            filings = []
            allowed = {"10-K", "10-Q", "8-K"}

            for form, date, accession in zip(forms, dates, accessions):
                if form in allowed:
                    filings.append({
                        "form": form,
                        "filingDate": date,
                        "accessionNumber": accession,
                    })
                if len(filings) == 5:
                    break
            self.cache[cache_key] = filings
            return filings
        
        except Exception:
            return []
        
    def calculate_days_since_filing(self, filing_date: str) -> int | None:
        """
        Calcuate days elapsed since the most recent SEC filing.
        filing_date format: "2024-11-15"
        Returns int days, or None if date parsing 
        """
        try:
            filing_datetime = datetime.strptime(filing_date, "%Y-%m-%d")
            return (datetime.now() - filing_datetime).days
        except Exception:
            return None
        
    def detect_risk_flags(self, filings_text: str) -> list[str]:
        """
        Scans filing content for regulatory red flags using keyword matching.
        Returns list of flag strings matching ComplianceReport.risk_flags.
        Returns empty list if no flags found.
        """
        try:
            detected = set()
            text_lower = filings_text.lower()

            for flag, keywords in self.risk_keywords.items():
                for keyword in keywords:
                    if keyword in text_lower:
                        detected.add(flag)
                        break

            return list(detected)

        except Exception:
            return []
        
    def calculate_risk_score(self, risk_flags: list[str]) -> float:
        """
        Converts list of risk_flags into a 0.0-1.0 risk score.
        Severe flags carry higher weight than minor ones.
        Return 0.0 if no flags. Clamped to 1.0 maximum.
        """
        flag_weights = {
            "going_concern": 0.40,
            "restatement": 0.35,
            "investigation": 0.35,
            "insider_selling": 0.20,
            "late_filing": 0.15
        }
        try:
            total = sum(flag_weights.get(flag, 0.1) for flag in risk_flags)
            return min(1.0, total)
        
        except Exception:
            return 0.0
        
    async def get_filing_risk(self, ticker: str) -> dict:
        """
        Main function called by ComplianceChecker.
        Combines all helpers into one call.
        Returns ComplianceReport - ready dict with latest_filings_type,
        days_since_filing, risk_flags, risk_score.
        Returns empty dict on failure.
        """
        try:
            filings = await self.get_recent_filings(ticker)
            if not filings:
                return {}
            
            most_recent = filings[0]
            latest_filing_type = most_recent["form"]
            days_since = self.calculate_days_since_filing(most_recent["filingDate"])
            risk_flags = self.detect_risk_flags(str(most_recent))
            risk_score = self.calculate_risk_score(risk_flags)

            return {
                "latest_filing_type": latest_filing_type,
                "days_since_filing": days_since,
                "risk_flags": risk_flags,
                "risk_score": risk_score,

            }
        except Exception:
            return {}
        
sec = SecConnector()
                       
