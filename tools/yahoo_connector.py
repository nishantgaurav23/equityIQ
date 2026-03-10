"""Yahoo Finance connector for universal stock data (US + India + global).

Uses yfinance for price history and search. Supports NSE (.NS), BSE (.BO),
and US tickers. Falls back gracefully if data is unavailable.
"""

from __future__ import annotations

import logging

from cachetools import TTLCache

logger = logging.getLogger(__name__)


# Common exchange rates (fallback). Updated via get_exchange_rate() when possible.
_FALLBACK_RATES: dict[str, float] = {
    "USD": 1.0,
    "INR": 83.5,
    "EUR": 0.92,
    "GBP": 0.79,
    "JPY": 149.5,
    "CAD": 1.36,
    "AUD": 1.53,
}


class YahooConnector:
    """Fetch price history and search for any market via Yahoo Finance."""

    def __init__(self) -> None:
        self.cache: TTLCache = TTLCache(maxsize=256, ttl=300)

    async def get_price_history(self, ticker: str, days: int = 90) -> dict:
        """Fetch daily OHLCV bars. Works for US, NSE (.NS), BSE (.BO) tickers.

        Returns {"prices": [...], "volumes": [...], "dates": [...], "currency": "USD"}
        or {} on error.
        """
        cache_key = f"yf_price_{ticker}_{days}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            import yfinance as yf

            period_map = {
                7: "7d",
                30: "1mo",
                90: "3mo",
                180: "6mo",
                365: "1y",
            }
            period = "3mo"
            for d, p in sorted(period_map.items()):
                if days <= d:
                    period = p
                    break
            else:
                period = "1y"

            stock = yf.Ticker(ticker)
            hist = stock.history(period=period)

            if hist.empty:
                return {}

            # Detect currency from ticker info, with suffix-based fallback
            try:
                info = stock.fast_info
                currency = getattr(info, "currency", None) or None
            except Exception:
                currency = None
            if not currency:
                t_upper = ticker.upper().strip()
                if t_upper.endswith(".NS") or t_upper.endswith(".BO"):
                    currency = "INR"
                elif t_upper.endswith(".L"):
                    currency = "GBP"
                elif t_upper.endswith(".TO") or t_upper.endswith(".V"):
                    currency = "CAD"
                else:
                    currency = "USD"

            prices = hist["Close"].tolist()
            volumes = hist["Volume"].tolist()
            dates = [d.strftime("%Y-%m-%d") for d in hist.index]

            result = {
                "prices": prices,
                "volumes": volumes,
                "dates": dates,
                "currency": currency.upper(),
            }
            self.cache[cache_key] = result
            return result
        except Exception as exc:
            logger.warning("Yahoo Finance error for %s: %s", ticker, exc)
            return {}

    async def get_fundamentals(self, ticker: str) -> dict:
        """Fetch fundamental financial ratios via yfinance.

        Returns dict matching PolygonConnector.get_fundamentals() shape:
        {pe_ratio, pb_ratio, revenue_growth, debt_to_equity, fcf_yield}.
        Returns {} on error.
        """
        cache_key = f"yf_fund_{ticker}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            import yfinance as yf

            stock = yf.Ticker(ticker)
            info = stock.info or {}

            if not info or info.get("regularMarketPrice") is None:
                return {}

            # Revenue growth as decimal fraction (0.05 = 5%). yfinance already
            # returns a decimal fraction, so no multiplication needed.
            raw_rev_growth = info.get("revenueGrowth")
            revenue_growth = round(raw_rev_growth, 4) if raw_rev_growth is not None else None

            # FCF yield as decimal fraction (0.05 = 5%)
            raw_fcf = info.get("freeCashflow")
            market_cap = info.get("marketCap")
            fcf_yield = None
            if raw_fcf is not None and market_cap and market_cap != 0:
                fcf_yield = round(raw_fcf / market_cap, 4)

            result = {
                "pe_ratio": info.get("trailingPE"),
                "pb_ratio": info.get("priceToBook"),
                "revenue_growth": revenue_growth,
                # yfinance returns debtToEquity as percentage (177.65 = 177.65%)
                # Normalize to ratio form (1.7765) to match Polygon convention
                "debt_to_equity": (
                    round(info["debtToEquity"] / 100, 2)
                    if info.get("debtToEquity") is not None
                    else None
                ),
                "fcf_yield": fcf_yield,
                "market_cap": market_cap,
                "eps": info.get("trailingEps"),
                "dividend_yield": info.get("dividendYield"),
                "currency": info.get("currency", "INR"),
            }

            self.cache[cache_key] = result
            return result
        except Exception as exc:
            logger.warning("Yahoo fundamentals error for %s: %s", ticker, exc)
            return {}

    async def get_company_info(self, ticker: str) -> dict:
        """Fetch basic company metadata: name, market cap, employees, sector, industry.

        Returns dict with keys matching CompanyInfo fields, or {} on error.
        """
        cache_key = f"yf_info_{ticker}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            import yfinance as yf

            stock = yf.Ticker(ticker)
            info = stock.info or {}

            if not info:
                return {}

            # Detect currency from ticker suffix
            t_upper = ticker.upper().strip()
            if t_upper.endswith(".NS") or t_upper.endswith(".BO"):
                currency = "INR"
            elif t_upper.endswith(".L"):
                currency = "GBP"
            elif t_upper.endswith(".TO") or t_upper.endswith(".V"):
                currency = "CAD"
            else:
                currency = info.get("currency", "USD")

            result = {
                "name": info.get("shortName") or info.get("longName"),
                "market_cap": info.get("marketCap"),
                "employees": info.get("fullTimeEmployees"),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "currency": currency.upper() if currency else "USD",
            }

            self.cache[cache_key] = result
            return result
        except Exception as exc:
            logger.warning("Yahoo company info error for %s: %s", ticker, exc)
            return {}

    async def search_tickers(self, query: str, limit: int = 10) -> list[dict]:
        """Search for tickers across all markets (US, India, global).

        Returns list of {ticker, name, market, type, locale}.
        """
        cache_key = f"yf_search_{query}_{limit}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            import yfinance as yf

            search = yf.Search(query, max_results=limit)
            results = []

            for quote in getattr(search, "quotes", [])[:limit]:
                exchange = quote.get("exchange", "")
                locale = (
                    "in"
                    if exchange in ("NSI", "BOM", "NSE", "BSE", "NMS")
                    and (
                        quote.get("symbol", "").endswith(".NS")
                        or quote.get("symbol", "").endswith(".BO")
                    )
                    else "us"
                )
                # Better locale detection
                symbol = quote.get("symbol", "")
                if symbol.endswith(".NS") or symbol.endswith(".BO"):
                    locale = "in"
                elif symbol.endswith(".L"):
                    locale = "gb"
                elif symbol.endswith(".T"):
                    locale = "jp"

                results.append(
                    {
                        "ticker": symbol,
                        "name": quote.get("shortname", quote.get("longname", "")),
                        "market": exchange,
                        "type": quote.get("quoteType", "equity").lower(),
                        "locale": locale,
                    }
                )

            self.cache[cache_key] = results
            return results
        except Exception as exc:
            logger.warning("Yahoo search error for %s: %s", query, exc)
            return []

    async def get_exchange_rate(self, from_currency: str, to_currency: str) -> float:
        """Get exchange rate between two currencies.

        Tries direct pair first (e.g. USDINR=X), then reverse pair (INRUSD=X)
        and inverts. Falls back to static rates. Returns 1.0 on total failure.
        """
        from_c = from_currency.upper()
        to_c = to_currency.upper()

        if from_c == to_c:
            return 1.0

        cache_key = f"yf_fx_{from_c}_{to_c}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            import yfinance as yf

            # Try direct pair: FROM->TO
            pair = f"{from_c}{to_c}=X"
            ticker = yf.Ticker(pair)
            hist = ticker.history(period="5d")
            if not hist.empty:
                rate = float(hist["Close"].iloc[-1])
                if rate > 0:
                    self.cache[cache_key] = rate
                    # Cache the reverse too
                    self.cache[f"yf_fx_{to_c}_{from_c}"] = 1.0 / rate
                    return rate

            # Try reverse pair: TO->FROM and invert
            reverse_pair = f"{to_c}{from_c}=X"
            ticker2 = yf.Ticker(reverse_pair)
            hist2 = ticker2.history(period="5d")
            if not hist2.empty:
                reverse_rate = float(hist2["Close"].iloc[-1])
                if reverse_rate > 0:
                    rate = 1.0 / reverse_rate
                    self.cache[cache_key] = rate
                    self.cache[f"yf_fx_{to_c}_{from_c}"] = reverse_rate
                    return rate
        except Exception as exc:
            logger.warning("FX rate error %s->%s: %s", from_c, to_c, exc)

        # Fallback: convert through USD using static rates
        # e.g., INR->EUR = (1/INR_per_USD) * EUR_per_USD
        if from_c in _FALLBACK_RATES and to_c in _FALLBACK_RATES:
            rate = _FALLBACK_RATES[to_c] / _FALLBACK_RATES[from_c]
            self.cache[cache_key] = rate
            return rate

        return 1.0

    async def get_multi_price_history(self, tickers: list[str], days: int = 90) -> dict[str, dict]:
        """Fetch price history for multiple tickers.

        Returns {ticker: {prices, volumes, dates, currency}} for each.
        Runs sequentially because yfinance is synchronous and concurrent calls
        can fail on resource-constrained environments (e.g. Cloud Run).
        """
        out: dict[str, dict] = {}
        for ticker in tickers:
            try:
                result = await self.get_price_history(ticker, days)
                if isinstance(result, dict) and result:
                    out[ticker] = result
            except Exception:
                logger.warning("Multi price history failed for %s", ticker)
        return out


yahoo = YahooConnector()
