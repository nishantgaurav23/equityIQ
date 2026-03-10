"""Chat engine and API routes for natural language chat interface (S16.2).

Redesigned to be a true conversational financial AI:
- Answers ANY question contextually (price, market cap, fundamentals, macro, general finance)
- Uses conversation history to avoid repeating itself
- Fetches lightweight data (price, company info) without running full 7-agent analysis
- Only triggers full multi-agent analysis when user explicitly asks for deep analysis
- Reuses prior analysis from conversation history for follow-up questions
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import uuid
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse

from config.data_contracts import (
    ChatHistoryResponse,
    ChatRequest,
    ChatResponse,
    ConversationEntry,
    FinalVerdict,
)

logger = logging.getLogger(__name__)

chat_router = APIRouter(prefix="/api/v1/chat", tags=["chat"])

# Ticker pattern: 1-12 uppercase letters, optionally with .NS/.BO/.L suffix
_TICKER_PATTERN = re.compile(r"\b([A-Z]{1,12}(?:\.(?:NS|BO|L))?)\b")

# Common English words that look like tickers but aren't
_TICKER_STOPWORDS = {
    "A", "I", "AM", "AN", "AS", "AT", "BE", "BY", "DO", "GO", "HE", "IF", "IN",
    "IS", "IT", "ME", "MY", "NO", "OF", "OK", "ON", "OR", "SO", "TO", "UP", "US",
    "WE", "ALL", "AND", "ARE", "BUT", "CAN", "DID", "FOR", "GET", "GOT", "HAS",
    "HAD", "HER", "HIM", "HIS", "HOW", "ITS", "LET", "MAY", "NEW", "NOT", "NOW",
    "OLD", "OUR", "OUT", "OWN", "SAY", "SHE", "THE", "TOO", "TRY", "USE", "WAY",
    "WHO", "WHY", "YOU", "YES", "YET", "ANY", "BIG", "DAY", "END", "FAR", "FEW",
    "RUN", "SET", "PUT", "SEE", "WHAT", "WHEN", "WILL", "WITH", "HAVE", "THIS",
    "THAT", "FROM", "THEY", "BEEN", "THAN", "THEM", "THEN", "SOME", "WERE", "MUCH",
    "ALSO", "BOTH", "EACH", "JUST", "LIKE", "LONG", "MAKE", "MANY", "MORE", "MOST",
    "ONLY", "OVER", "SUCH", "TAKE", "VERY", "YOUR", "SELL", "HOLD", "HIGH", "RISK",
    "LAST", "GOOD", "WELL", "HELP", "TELL", "BUY", "PE", "EPS", "GDP", "IPO", "ETF",
    "RSI", "SMA", "ATH", "FED", "SEC", "CEO", "CFO", "CTO", "ROI", "ROE", "YOY",
    "QOQ", "MOM", "DAD", "NET", "TOP", "LOW", "MAX", "MIN", "AVG", "SUM", "ADD",
    "ABOUT", "AFTER", "AGAIN", "BELOW", "COULD", "EVERY", "FIRST", "FOUND",
    "GREAT", "NEVER", "OTHER", "PRICE", "RIGHT", "SHALL", "SHOW", "SINCE",
    "STILL", "THEIR", "THERE", "THESE", "THINK", "THREE", "TODAY", "UNDER",
    "UNTIL", "WHERE", "WHILE", "WOULD", "ABOVE", "BEING", "GOING", "GIVES",
    "KEEPS", "KNOWN", "LARGE", "LATER", "LOOKS", "MIGHT", "NEEDS", "OFTEN",
    "POINT", "QUITE", "SMALL", "START", "STOCK", "TRADE", "USING", "VALUE",
    "WORLD", "WORSE", "WORST", "YEARS", "MARKET", "SIGNAL", "STRONG",
    "GROWTH", "BETTER", "PLEASE", "REALLY", "SHOULD", "THANKS", "VERSUS",
    "ALWAYS", "BEFORE", "BUYING", "DURING", "HIGHER", "INVEST", "LOSSES",
    "MOVING", "OPTION", "PROFIT", "RETURN", "SECTOR", "VOLUME", "WEEKLY",
    "ANNUAL", "ASSETS", "CHANGE", "EQUITY", "MARGIN", "YIELDS", "SHARES",
    "REPORT", "RATING", "TARGET", "INCOME", "CHARTS", "TRENDS", "GLOBAL",
    "COMPARE", "ANALYZE", "ANALYSE", "PREDICT", "BETWEEN", "AGAINST",
    "BECAUSE", "OVERALL", "ANOTHER", "ALREADY", "THROUGH", "WITHOUT",
    "HOWEVER", "WHETHER", "NOTHING", "LOOKING", "FURTHER", "CURRENT",
    "QUARTER", "MONTHLY", "TRADING", "AVERAGE", "HISTORY", "DISPLAY",
    "SUGGEST", "OPINION", "BELIEVE", "PERFORM", "GENERAL", "FINANCE",
    "EARNING", "CAPITAL", "BILLION", "MILLION", "PERCENT", "DIVIDEND",
    "FORECAST", "ANALYSIS", "MOMENTUM", "EARNINGS", "ESTIMATE", "STRATEGY",
    "ECONOMIC", "INFLATION", "INTEREST", "PORTFOLIO", "POSITION",
    "TECHNICAL", "FINANCIAL", "SENTIMENT", "VALUATION", "INDICATOR",
    "RECOMMEND", "BENCHMARK", "VOLATILITY", "COMPLIANCE", "RECESSION",
    "QUARTERLY", "VISUALIZE", "VISUALISE",
    # Stock exchange names — NOT tickers
    "NSE", "BSE", "NYSE", "NASDAQ", "NIFTY", "SENSEX", "FTSE", "DJIA",
    "LSE", "SGX", "ASX", "TSX", "HKEX", "SSE", "SZSE", "KRX", "KOSPI",
    "EXCHANGE", "BOMBAY", "NATIONAL",
}

# Words that look like company names but aren't (avoid searching for these)
_NAME_STOPWORDS = {
    "the", "and", "for", "are", "but", "not", "you", "all", "can", "had",
    "her", "was", "one", "our", "out", "has", "how", "its", "may", "new",
    "now", "say", "she", "too", "use", "way", "who", "why", "yet", "any",
    "big", "day", "end", "far", "few", "run", "set", "put", "see", "did",
    "get", "let", "old", "own", "try", "also", "both", "each", "just",
    "like", "long", "make", "many", "more", "most", "only", "over", "such",
    "take", "very", "your", "tell", "show", "help", "good", "well", "last",
    "some", "what", "when", "will", "with", "have", "this", "that", "from",
    "they", "been", "than", "them", "then", "were", "much", "compare",
    "analyze", "analyse", "visualize", "visualise", "chart", "graph",
    "plot", "draw", "display", "trend", "stock", "stocks", "price",
    "market", "markets", "signal", "signals", "risk", "high", "low",
    "medium", "hold", "sell", "buy", "strong", "about", "think",
    "ratio", "growth", "rate", "value", "yield", "debt", "earnings",
    "revenue", "profit", "loss", "income", "margin", "return", "beta",
    "target", "level", "score", "data", "index", "fund", "bond",
    "call", "option", "future", "share", "shares", "sector", "cap",
    "volume", "average", "momentum", "sentiment", "economy", "macro",
    "inflation", "interest", "dividend", "valuation", "fundamental",
    "technical", "compliance", "filing", "report", "quarter", "annual",
    "forecast", "prediction", "portfolio", "position", "size", "weight",
    "better", "worse", "best", "worst", "should", "could", "would",
    "which", "between", "versus", "against", "than", "going",
    "doing", "current", "recent", "today", "india", "indian",
    "affect", "affects", "difference", "explain", "stocks",
    "capitalization", "understand", "meaning", "means", "work",
    "works", "example", "examples", "type", "types", "kind", "kinds",
    "invest", "investing", "investor", "investors", "money",
    "concept", "concepts", "define", "definition", "definitions",
    "hello", "hey", "hi", "thanks", "thank", "please", "sorry",
    "does", "reasoning", "reason", "reasons", "because", "since",
    "would", "could", "should", "impact", "impacts", "impacting",
    "whether", "however", "although", "though", "still", "also",
    "give", "gives", "gave", "given", "much", "really",
    "different", "same", "similar", "important", "generally",
    "there", "here", "where", "federal", "reserve", "rates",
    "between", "during", "after", "before", "above", "below",
    "these", "those", "other", "another", "every", "first",
    "second", "third", "next", "last", "right", "wrong",
    "what", "when", "where", "which", "how", "why", "who",
}


# ---------------------------------------------------------------------------
# Ticker / company name helpers
# ---------------------------------------------------------------------------

async def resolve_company_names(message: str, known_tickers: list[str]) -> list[str]:
    """Resolve company names to ticker symbols using Yahoo Finance + Polygon search."""
    lower = message.lower()
    single_words = lower.split()

    known_upper = {t.upper() for t in known_tickers}
    candidates: list[str] = []
    for w in single_words:
        w_clean = w.strip(".,!?()\"'")
        if (
            len(w_clean) >= 3
            and w_clean not in _NAME_STOPWORDS
            and w_clean.upper() not in _TICKER_STOPWORDS
            and w_clean.upper() not in known_upper
        ):
            candidates.append(w_clean)

    if not candidates:
        return []

    # Two-word phrases (e.g. "tata motors", "coca cola")
    bigrams: list[str] = []
    for i in range(len(single_words) - 1):
        w1 = single_words[i].strip(".,!?()\"'")
        w2 = single_words[i + 1].strip(".,!?()\"'")
        if w1 not in _NAME_STOPWORDS and w2 not in _NAME_STOPWORDS:
            bigrams.append(f"{w1} {w2}")

    resolved: list[str] = []
    searched: set[str] = set()

    for candidate in bigrams + candidates:
        if candidate in searched:
            continue
        searched.add(candidate)

        try:
            from tools.yahoo_connector import yahoo
            results = await yahoo.search_tickers(candidate, limit=3)

            if not results:
                from tools.ticker_search import search_tickers
                results = await search_tickers(candidate, limit=3)

            if results:
                ticker = results[0]["ticker"]
                name = results[0].get("name", "").lower()
                if (
                    candidate in name
                    or name.startswith(candidate)
                    or ticker.lower().startswith(candidate[:3])
                ):
                    if ticker not in known_upper and ticker not in resolved:
                        resolved.append(ticker)
                        if " " in candidate:
                            for part in candidate.split():
                                searched.add(part)
        except Exception:
            logger.debug("Search failed for candidate: %s", candidate)

    return resolved


def extract_tickers(message: str) -> list[str]:
    """Extract uppercase ticker symbols from a message (sync, fast)."""
    found: list[str] = []
    for t in _TICKER_PATTERN.findall(message):
        if t not in _TICKER_STOPWORDS:
            found.append(t)
    return found


def _has_potential_company_names(message: str) -> bool:
    """Check if message contains words that might be company names (not tickers)."""
    for w in message.split():
        w_clean = w.strip(".,!?()\"'")
        w_lower = w_clean.lower()
        if (
            len(w_clean) >= 3
            and w_lower not in _NAME_STOPWORDS
            and w_clean not in _TICKER_STOPWORDS
            and not w_clean.isupper()
        ):
            return True
    return False


# ---------------------------------------------------------------------------
# Market context helpers
# ---------------------------------------------------------------------------

def _mentions_indian_market(message_lower: str) -> bool:
    """Check if the message references Indian stock exchanges or markets."""
    indian_keywords = [
        "nse", "bse", "bombay", "national stock exchange",
        "bombay stock exchange", "indian market", "indian exchange",
        "india market", "india exchange", "indian stock",
        "in india", "in rupees", "in inr", "inr price",
        "nifty", "sensex", "rupee",
    ]
    return any(kw in message_lower for kw in indian_keywords)


# ---------------------------------------------------------------------------
# Intent detection — now distinguishes "full analysis" from "quick question"
# ---------------------------------------------------------------------------

def _wants_visual(message: str) -> bool:
    """Check if the user wants a visual/chart/graph output."""
    lower = message.lower()
    return any(
        kw in lower
        for kw in [
            "visuali", "graph", "chart", "plot",
            "price history", "price chart", "draw", "display",
            "show me the chart", "show me the graph", "show chart",
            "show the trend", "show trend", "price trend",
            "show me the trend", "show price",
        ]
    )


def detect_intent(message: str) -> str:
    """Classify user message intent.

    Returns one of:
    - 'greeting': casual greeting (hi, hello, hey, etc.)
    - 'full_analysis': deep multi-agent analysis (explicit request)
    - 'visualize': analysis + show chart
    - 'visualize_context': show chart for contextual ticker
    - 'compare': compare multiple stocks
    - 'quick_question': specific question about a stock (price, market cap, etc.)
    - 'follow_up': references prior conversation context
    - 'general': general finance/economy question, no specific stock
    """
    lower = message.lower().strip()

    # Greeting — short casual messages
    greeting_words = {
        "hi", "hello", "hey", "howdy", "hola", "yo", "sup",
        "good morning", "good evening", "good afternoon",
        "what's up", "whats up", "wassup",
    }
    # Exact match or very short greeting-like message
    stripped = lower.rstrip("!?.,:; ")
    if stripped in greeting_words or (
        len(lower.split()) <= 3 and any(
            lower.startswith(g) for g in greeting_words
        )
    ):
        return "greeting"

    tickers = extract_tickers(message)
    has_names = _has_potential_company_names(message)
    has_subjects = bool(tickers) or has_names

    # Compare intent
    is_compare = any(kw in lower for kw in ["compare", " vs ", " versus ", "which is better"])
    is_visual = _wants_visual(lower)

    if is_compare and has_subjects:
        return "visualize" if is_visual else "compare"

    if is_visual and has_subjects:
        return "visualize"

    if is_visual:
        return "visualize_context"

    # Bare ticker(s) with very short message -> full analysis
    # e.g. "AAPL", "TSLA RIVN"
    if tickers and not has_names and len(lower.split()) <= 2:
        return "full_analysis"

    # Full analysis: user explicitly asks for deep/comprehensive analysis
    full_analysis_keywords = [
        "analyze", "analysis", "analyse", "full analysis",
        "deep dive", "evaluate", "run analysis",
        "detailed analysis", "comprehensive",
    ]
    if any(kw in lower for kw in full_analysis_keywords) and has_subjects:
        return "full_analysis"

    # Follow-up intent — requires referencing prior context specifically
    follow_up_keywords = [
        "why did you", "why is it", "what made you",
        "tell me more", "elaborate", "go deeper", "can you clarify",
        "what does that mean", "why sell", "why buy", "why hold",
        "reason for", "reasoning behind",
    ]
    if any(kw in lower for kw in follow_up_keywords):
        return "follow_up"

    # "Explain" is follow_up only when it references prior context (no stock)
    # "Explain the PE ratio" -> general, "Explain why you said sell" -> follow_up
    if "explain" in lower and not has_subjects:
        # Check if it references prior analysis context
        if any(kw in lower for kw in [
            "your", "you said", "that", "the reasoning", "the signal",
            "the verdict", "the analysis",
        ]):
            return "follow_up"
        # Otherwise it's a general knowledge question
        return "general"

    # Quick question about a stock — any question mentioning a company/ticker
    # that is NOT a full analysis request
    if has_subjects:
        return "quick_question"

    return "general"


# ---------------------------------------------------------------------------
# Data fetching helpers — lightweight, no full pipeline
# ---------------------------------------------------------------------------

async def _fetch_quick_data(ticker: str) -> str:
    """Fetch lightweight data for a ticker: company info, price, fundamentals.

    This is FAST (~1-2s) vs full analysis (~30-60s). Used for quick questions.
    """
    parts: list[str] = []

    try:
        from tools.yahoo_connector import yahoo

        # Fetch company info, fundamentals, and recent price in parallel
        info_task = yahoo.get_company_info(ticker)
        fund_task = yahoo.get_fundamentals(ticker)
        price_task = yahoo.get_price_history(ticker, days=30)

        info, fund, price_data = await asyncio.gather(
            info_task, fund_task, price_task, return_exceptions=True,
        )

        # Company info
        if isinstance(info, dict) and info:
            name = info.get("name", ticker)
            parts.append(f"Company: {name} ({ticker})")
            if info.get("sector"):
                parts.append(f"Sector: {info['sector']}")
            if info.get("industry"):
                parts.append(f"Industry: {info['industry']}")
            currency = info.get("currency", "USD")
            if info.get("market_cap"):
                mc = info["market_cap"]
                if mc >= 1e12:
                    parts.append(
                        f"Market Cap: {currency} {mc / 1e12:.2f} Trillion"
                    )
                elif mc >= 1e9:
                    parts.append(
                        f"Market Cap: {currency} {mc / 1e9:.2f} Billion"
                    )
                elif mc >= 1e6:
                    parts.append(
                        f"Market Cap: {currency} {mc / 1e6:.2f} Million"
                    )
                else:
                    parts.append(f"Market Cap: {currency} {mc:,.0f}")
            if info.get("employees"):
                parts.append(f"Employees: {info['employees']:,}")

        # Current price from recent history
        if isinstance(price_data, dict) and price_data.get("prices"):
            prices = price_data["prices"]
            currency = price_data.get("currency", "USD")
            current = prices[-1]
            parts.append(f"Current Price: {currency} {current:,.2f}")

            if len(prices) >= 2:
                prev = prices[-2]
                day_change = current - prev
                day_pct = (day_change / prev) * 100 if prev else 0
                sign = "+" if day_change >= 0 else ""
                parts.append(
                    f"Day Change: {sign}{day_change:,.2f} ({sign}{day_pct:.2f}%)"
                )

            if len(prices) >= 5:
                week_ago = prices[-5] if len(prices) >= 5 else prices[0]
                week_change = ((current - week_ago) / week_ago) * 100
                sign = "+" if week_change >= 0 else ""
                parts.append(f"5-Day Change: {sign}{week_change:.2f}%")

            if len(prices) >= 20:
                month_ago = prices[-20]
                month_change = ((current - month_ago) / month_ago) * 100
                sign = "+" if month_change >= 0 else ""
                parts.append(f"~1 Month Change: {sign}{month_change:.2f}%")

            parts.append(f"30-Day High: {currency} {max(prices):,.2f}")
            parts.append(f"30-Day Low: {currency} {min(prices):,.2f}")

        # Fundamentals
        if isinstance(fund, dict) and fund:
            parts.append("\nFundamentals:")
            if fund.get("pe_ratio") is not None:
                parts.append(f"  P/E Ratio: {fund['pe_ratio']:.2f}")
            if fund.get("pb_ratio") is not None:
                parts.append(f"  P/B Ratio: {fund['pb_ratio']:.2f}")
            if fund.get("eps") is not None:
                parts.append(f"  EPS: {fund['eps']:.2f}")
            if fund.get("revenue_growth") is not None:
                rg = fund["revenue_growth"] * 100
                sign = "+" if rg >= 0 else ""
                parts.append(f"  Revenue Growth: {sign}{rg:.1f}%")
            if fund.get("debt_to_equity") is not None:
                parts.append(f"  Debt/Equity: {fund['debt_to_equity']:.2f}")
            if fund.get("fcf_yield") is not None:
                parts.append(f"  FCF Yield: {fund['fcf_yield'] * 100:.2f}%")
            if fund.get("dividend_yield") is not None:
                parts.append(
                    f"  Dividend Yield: {fund['dividend_yield'] * 100:.2f}%"
                )
            if fund.get("market_cap") and not any("Market Cap" in p for p in parts):
                mc = fund["market_cap"]
                curr = fund.get("currency", "USD")
                if mc >= 1e12:
                    parts.append(f"  Market Cap: {curr} {mc / 1e12:.2f}T")
                elif mc >= 1e9:
                    parts.append(f"  Market Cap: {curr} {mc / 1e9:.2f}B")
                else:
                    parts.append(f"  Market Cap: {curr} {mc / 1e6:.2f}M")

    except Exception as exc:
        logger.warning("Quick data fetch failed for %s: %s", ticker, exc)
        parts.append(f"Note: Could not fetch live data for {ticker}.")

    # Enrich with web search intelligence (Serper + Tavily)
    try:
        from tools.web_search import search_stock_intelligence, format_web_context
        web_data = await search_stock_intelligence(ticker)
        web_context = format_web_context(web_data, "Latest Web Intelligence")
        if web_context:
            parts.append(f"\n{web_context}")
    except Exception:
        logger.debug("Web search enrichment failed for %s", ticker)

    return "\n".join(parts) if parts else f"No data available for {ticker}."


# ---------------------------------------------------------------------------
# Format full analysis context (richer than before — includes key_metrics)
# ---------------------------------------------------------------------------

def _format_verdict_context(verdict: FinalVerdict) -> str:
    """Format a FinalVerdict into detailed context for the LLM prompt."""
    lines = [
        f"## Full Multi-Agent Analysis for {verdict.ticker}",
        f"Signal: {verdict.final_signal} "
        f"(confidence: {verdict.overall_confidence:.0%})",
        f"Risk Level: {verdict.risk_level}",
    ]

    # Company info
    if verdict.company_info:
        ci = verdict.company_info
        if ci.name:
            lines.append(f"Company: {ci.name}")
        if ci.sector:
            lines.append(f"Sector: {ci.sector} | Industry: {ci.industry or 'N/A'}")
        if ci.market_cap:
            curr = ci.currency or "USD"
            mc = ci.market_cap
            if mc >= 1e12:
                lines.append(f"Market Cap: {curr} {mc / 1e12:.2f} Trillion")
            elif mc >= 1e9:
                lines.append(f"Market Cap: {curr} {mc / 1e9:.2f} Billion")
            else:
                lines.append(f"Market Cap: {curr} {mc / 1e6:.2f} Million")

    if verdict.price_target:
        lines.append(f"Price Target: {verdict.price_target:.2f}")
    if verdict.risk_summary:
        lines.append(f"Risk Summary: {verdict.risk_summary}")

    if verdict.key_drivers:
        lines.append("\nKey Drivers:")
        for driver in verdict.key_drivers:
            lines.append(f"  - {driver}")

    if verdict.analyst_details:
        lines.append("\nAgent Reports:")
        for name, detail in verdict.analyst_details.items():
            lines.append(
                f"\n  {name}: {detail.signal} "
                f"({detail.confidence:.0%}) -- {detail.reasoning}"
            )
            # Include key_metrics so the model has actual numbers
            if detail.key_metrics:
                for k, v in detail.key_metrics.items():
                    lines.append(f"    {k}: {v}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# System prompt — completely rewritten for contextual conversation
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are EquityIQ, an expert financial AI assistant. You have deep knowledge of \
stock markets (US, India, global), finance, economics, investing, and trading.

## Core Behavior
- ANSWER THE SPECIFIC QUESTION the user asked. Do NOT dump a full analysis \
report for every question. If they ask for the stock price, give the stock \
price. If they ask about market cap, give market cap. If they ask a general \
finance question, answer it directly.
- Use the data provided in the context to answer. The context contains real-time \
data fetched from APIs — use the actual numbers, do not say "I don't have this data" \
when it is in the context.
- Be conversational. Short answers for short questions. Detailed answers for \
detailed questions. Match the depth of your response to the depth of the question.
- When the user has asked about a stock before in this conversation, you already \
know about it. Reference prior discussion naturally, do NOT repeat the same \
information unless specifically asked.
- You CAN answer general finance questions (What is a PE ratio? How does \
inflation affect stocks? What is market cap?) without needing any stock data.
- Never give specific buy/sell financial advice — present findings objectively.
- Many stocks are listed on MULTIPLE exchanges (e.g., INFY trades on NYSE as INFY \
and on NSE as INFY.NS and BSE as INFY.BO). When the user asks about a stock on a \
specific exchange (NSE, BSE, Indian market), use the data for the .NS or .BO ticker \
from the context. Always present the data you HAVE — never say "I don't have data" \
when it IS in the context below.

## Greetings & Casual Chat
- If the user says hi, hello, hey, good morning, etc., respond warmly and \
conversationally. Introduce yourself briefly: "Hey! I'm EquityIQ, your AI \
stock analyst. Ask me about any stock, market trends, or financial concepts. \
What would you like to explore today?"
- Keep it friendly and natural — you're a helpful financial companion.
- You can handle casual conversation — just gently steer toward finance if appropriate.

## Ask for Clarification
- This is a CHAT — you can and SHOULD ask clarification questions when needed.
- If the user asks something ambiguous (e.g., "show the trend" without mentioning \
a stock), ask: "Which stock would you like me to show the trend for?"
- If the user says "visualize" or "chart" without a ticker and there's no stock \
in the conversation history, ask which stock they want.
- If the question is unclear, ask a short clarifying question rather than guessing.
- Never hallucinate data — if you don't have data for a stock, say so and offer \
to look it up.

## Visualization Responses
- When showing a chart/visualization, provide brief commentary on what the chart \
shows: current price, recent trend direction, notable moves.
- The chart is rendered by the UI automatically — do NOT try to draw ASCII charts.
- Default timeframe is 3 months if the user doesn't specify.

## When to give detailed analysis
Only provide a comprehensive multi-agent breakdown when:
1. The user explicitly asks: "analyze", "full analysis", "deep dive", "evaluate"
2. It's the FIRST time discussing a stock and the context includes full analysis data
For follow-up questions about the SAME stock, answer concisely using the data \
you already have. Do NOT repeat the full report.

## Using conversation history
- The conversation history is provided. Read it carefully.
- If the user previously asked about BHEL and now asks "what is the stock price?", \
you know they mean BHEL's stock price.
- Do NOT repeat information you already shared. If you already gave a full \
analysis, don't give it again. Answer the new specific question.

## Formatting (your output is rendered as Markdown)
- Use ## for major sections, ### for subsections
- Use **bold** for key terms, signals (BUY, SELL, HOLD), and important numbers
- Use bullet points for lists
- Use > blockquotes for key verdicts or takeaways
- Use tables when comparing data points or summarizing metrics
- Prefix positive values with + (e.g. +2.03%), negative with - (e.g. -24.2%)
- Keep paragraphs short (2-3 sentences)
"""


# ---------------------------------------------------------------------------
# Chat Engine
# ---------------------------------------------------------------------------

class ChatEngine:
    """Orchestrates chat: context retrieval, LLM generation, storage."""

    def __init__(self, conductor=None, memory=None, vault=None):
        self._conductor = conductor
        self._memory = memory
        self._vault = vault

    async def process_message(
        self, request: ChatRequest
    ) -> AsyncGenerator[dict, None]:
        """Process a chat message and yield SSE events."""
        session_id = request.session_id or str(uuid.uuid4())
        yield {"type": "session", "session_id": session_id}

        intent = detect_intent(request.message)
        tickers = extract_tickers(request.message)

        # Skip heavy processing for greetings
        if intent == "greeting":
            tickers = []

        # Resolve company names to tickers (e.g. "BHEL" already uppercase,
        # "apple" -> AAPL, "tata motors" -> TATAMOTORS.NS)
        if intent != "greeting" and _has_potential_company_names(request.message):
            try:
                resolved = await resolve_company_names(
                    request.message, tickers
                )
                tickers.extend(resolved)
                logger.info(
                    "Resolved company names: %s -> %s",
                    request.message, resolved,
                )
            except Exception:
                logger.warning(
                    "Company name resolution failed, continuing with: %s",
                    tickers,
                )

        ticker = request.ticker or (tickers[0] if tickers else None)
        verdict_session_id = None
        analyzed_tickers: list[str] = []
        show_charts = intent in ("visualize", "visualize_context")

        context_parts: list[str] = []
        history_entries: list[ConversationEntry] = []

        # Retrieve conversation history
        if self._memory:
            try:
                history_entries = await self._memory.get_conversation(
                    session_id, limit=20
                )
            except Exception:
                logger.exception("Failed to retrieve conversation history")

        # If no ticker found in message, try to infer from conversation history
        if not ticker and history_entries:
            for entry in reversed(history_entries):
                if entry.ticker:
                    ticker = entry.ticker
                    if ticker not in tickers:
                        tickers.append(ticker)
                    break

        # ---- Route by intent ----

        if intent == "full_analysis" and ticker and self._conductor:
            # Full multi-agent analysis — only when explicitly requested
            if len(tickers) <= 1:
                try:
                    verdict = await asyncio.wait_for(
                        self._conductor.analyze(ticker), timeout=60
                    )
                    context_parts.append(_format_verdict_context(verdict))
                    verdict_session_id = verdict.session_id
                    analyzed_tickers.append(ticker)
                except Exception:
                    logger.exception("Analysis failed for %s", ticker)
                    context_parts.append(
                        f"Note: Full analysis for {ticker} failed. "
                        "Answering from general knowledge."
                    )
            else:
                # Multiple tickers for full analysis
                for t in tickers[:3]:
                    try:
                        v = await asyncio.wait_for(
                            self._conductor.analyze(t), timeout=60
                        )
                        context_parts.append(_format_verdict_context(v))
                        if not verdict_session_id:
                            verdict_session_id = v.session_id
                        analyzed_tickers.append(t)
                    except Exception:
                        logger.exception("Analysis failed for %s", t)

        elif intent == "compare" and len(tickers) >= 2 and self._conductor:
            # Compare — needs full analysis for each
            for t in tickers[:3]:
                try:
                    v = await asyncio.wait_for(
                        self._conductor.analyze(t), timeout=60
                    )
                    context_parts.append(_format_verdict_context(v))
                    if not verdict_session_id:
                        verdict_session_id = v.session_id
                    analyzed_tickers.append(t)
                except Exception:
                    logger.exception("Comparison analysis failed for %s", t)

        elif intent == "visualize" and tickers:
            # Visualize — full analysis + chart
            show_charts = True
            if self._conductor:
                for t in tickers[:3]:
                    try:
                        v = await asyncio.wait_for(
                            self._conductor.analyze(t), timeout=60
                        )
                        context_parts.append(_format_verdict_context(v))
                        if not verdict_session_id:
                            verdict_session_id = v.session_id
                        analyzed_tickers.append(t)
                    except Exception:
                        logger.exception("Analysis failed for %s", t)

        elif intent == "visualize_context":
            # Show chart for contextual ticker — no full analysis needed,
            # the chart component fetches price data on its own
            if ticker:
                show_charts = True
                analyzed_tickers.append(ticker)
                # Fetch lightweight data for brief commentary
                quick_data = await _fetch_quick_data(ticker)
                context_parts.append(
                    f"--- Live Data for {ticker} ---\n{quick_data}"
                )
                # Also check for prior analysis in conversation
                prior = self._find_prior_analysis(history_entries, ticker)
                if prior:
                    context_parts.append(
                        f"[Prior analysis for {ticker} — use for "
                        f"brief commentary]\n{prior[:300]}"
                    )
            else:
                # No ticker found — LLM should ask which stock to visualize
                show_charts = False
                context_parts.append(
                    "[No stock ticker identified. Ask the user which "
                    "stock they want to visualize/chart.]"
                )

        elif intent == "quick_question" and ticker:
            # Quick question — fetch lightweight data, no full pipeline
            # First check if we have prior analysis in conversation history
            prior_analysis = self._find_prior_analysis(history_entries, ticker)
            if prior_analysis:
                context_parts.append(
                    f"[Prior analysis context for {ticker} from this "
                    f"conversation — use to answer, do NOT repeat in full]\n"
                    f"{prior_analysis}"
                )

            # Detect if user is asking about Indian exchange specifically
            msg_lower = request.message.lower()
            wants_indian = _mentions_indian_market(msg_lower)

            # Always fetch fresh lightweight data (price, fundamentals, info)
            quick_data = await _fetch_quick_data(ticker)
            context_parts.append(
                f"--- Live Data for {ticker} ---\n{quick_data}"
            )

            # If user wants Indian market data and ticker has no exchange suffix,
            # also fetch .NS and .BO variants
            if wants_indian and "." not in ticker:
                for suffix in (".NS", ".BO"):
                    indian_ticker = f"{ticker}{suffix}"
                    indian_data = await _fetch_quick_data(indian_ticker)
                    if "No data available" not in indian_data:
                        exchange = "NSE" if suffix == ".NS" else "BSE"
                        context_parts.append(
                            f"--- {exchange} Data for {indian_ticker} ---\n"
                            f"{indian_data}"
                        )

            # Also fetch for additional tickers if mentioned
            for t in tickers[1:3]:
                extra = await _fetch_quick_data(t)
                context_parts.append(f"--- Live Data for {t} ---\n{extra}")

        elif intent == "follow_up":
            # Follow-up — reuse prior analysis from conversation or vault
            if ticker:
                prior = self._find_prior_analysis(history_entries, ticker)
                if prior:
                    context_parts.append(
                        f"[Prior analysis for {ticker} — answer the "
                        f"follow-up using this data]\n{prior}"
                    )
                elif self._vault:
                    try:
                        from memory.history_retriever import HistoryRetriever
                        retriever = HistoryRetriever(self._vault)
                        verdicts = await retriever.get_ticker_history(
                            ticker, limit=1
                        )
                        if verdicts:
                            context_parts.append(
                                _format_verdict_context(verdicts[0])
                            )
                            verdict_session_id = verdicts[0].session_id
                    except Exception:
                        logger.exception("Failed to retrieve follow-up data")
            elif history_entries:
                last_with_ticker = next(
                    (e for e in reversed(history_entries) if e.ticker), None
                )
                if last_with_ticker and last_with_ticker.verdict_session_id:
                    try:
                        v = await self._vault.get_verdict(
                            last_with_ticker.verdict_session_id
                        )
                        if v:
                            context_parts.append(_format_verdict_context(v))
                            ticker = last_with_ticker.ticker
                            verdict_session_id = (
                                last_with_ticker.verdict_session_id
                            )
                    except Exception:
                        pass

        # For "general" intent — enrich with web search if available
        if intent == "general" and not context_parts:
            try:
                from tools.web_search import search_general, format_web_context
                web_data = await search_general(request.message)
                web_ctx = format_web_context(
                    web_data, "Web Research"
                )
                if web_ctx:
                    context_parts.append(web_ctx)
            except Exception:
                logger.debug("Web search failed for general question")

        # Build LLM prompt
        prompt = self._build_prompt(
            request.message, context_parts, history_entries, intent
        )

        # Generate response via Gemini
        full_response = ""
        try:
            async for token in self._generate_streaming(
                prompt, history_entries
            ):
                full_response += token
                yield {"type": "token", "content": token}
        except Exception:
            logger.exception("Gemini generation failed")
            full_response = (
                "I'm sorry, I encountered an error generating a response. "
                "Please try again."
            )
            yield {"type": "token", "content": full_response}

        # Send context event with the primary ticker
        if ticker:
            yield {
                "type": "context",
                "ticker": ticker,
                "verdict_session_id": verdict_session_id,
            }

        # Send chart event
        chart_tickers = analyzed_tickers if analyzed_tickers else tickers
        if show_charts and chart_tickers:
            yield {"type": "chart", "tickers": chart_tickers}

        # Store conversation entries
        if self._memory:
            try:
                user_entry = ConversationEntry(
                    entry_id=str(uuid.uuid4()),
                    user_id=request.user_id,
                    session_id=session_id,
                    role="user",
                    content=request.message,
                    ticker=ticker,
                )
                await self._memory.store_conversation_entry(user_entry)

                assistant_entry = ConversationEntry(
                    entry_id=str(uuid.uuid4()),
                    user_id=request.user_id,
                    session_id=session_id,
                    role="assistant",
                    content=full_response,
                    ticker=ticker,
                    verdict_session_id=verdict_session_id,
                )
                await self._memory.store_conversation_entry(assistant_entry)
            except Exception:
                logger.exception("Failed to persist conversation")

        yield {
            "type": "done",
            "full_response": full_response,
            "session_id": session_id,
        }

    def _find_prior_analysis(
        self, history: list[ConversationEntry], ticker: str
    ) -> str | None:
        """Search conversation history for prior analysis of a ticker."""
        ticker_upper = ticker.upper()
        for entry in reversed(history):
            if (
                entry.role == "assistant"
                and entry.ticker
                and entry.ticker.upper() == ticker_upper
                and len(entry.content) > 200
            ):
                return entry.content
        return None

    async def process_message_sync(self, request: ChatRequest) -> ChatResponse:
        """Non-streaming version: collects all events and returns ChatResponse."""
        session_id = None
        full_response = ""
        ticker = None
        verdict_session_id = None

        async for event in self.process_message(request):
            if event["type"] == "session":
                session_id = event["session_id"]
            elif event["type"] == "context":
                ticker = event.get("ticker")
                verdict_session_id = event.get("verdict_session_id")
            elif event["type"] == "done":
                full_response = event.get("full_response", "")

        return ChatResponse(
            session_id=session_id or str(uuid.uuid4()),
            response=full_response,
            ticker=ticker,
            verdict_session_id=verdict_session_id,
        )

    def _build_prompt(
        self,
        message: str,
        context_parts: list[str],
        history: list[ConversationEntry],
        intent: str,
    ) -> str:
        """Build the full prompt with system instructions, context, history."""
        parts = [_SYSTEM_PROMPT]

        # Add intent hint so the model knows what kind of response to give
        intent_hints = {
            "greeting": (
                "The user is greeting you. Respond warmly and introduce "
                "yourself briefly as EquityIQ. Invite them to ask about "
                "stocks, markets, or financial concepts. Keep it short "
                "and friendly — 2-3 sentences max."
            ),
            "full_analysis": (
                "The user wants a comprehensive multi-agent analysis. "
                "Give a thorough breakdown."
            ),
            "compare": (
                "The user wants a comparison. Include a comparison table."
            ),
            "visualize": (
                "The user wants analysis with visualization. "
                "A price chart will be shown separately by the UI."
            ),
            "visualize_context": (
                "The user wants a chart/visualization. A price chart will "
                "be rendered by the UI below your response. Give a brief "
                "commentary on the stock's recent price action using the "
                "data provided. If no stock is identified, ask the user "
                "which stock they want to visualize."
            ),
            "quick_question": (
                "The user has a SPECIFIC question. Answer it directly and "
                "concisely using the data below. Do NOT give a full analysis "
                "report. Do NOT repeat information from prior conversation. "
                "Just answer the question asked."
            ),
            "follow_up": (
                "The user is following up on a prior discussion. "
                "Answer based on what was discussed before. Be concise."
            ),
            "general": (
                "General finance/economy question or casual chat. "
                "If it's a greeting, respond warmly. If it's a finance "
                "question, answer from your knowledge. If unclear, ask "
                "a clarifying question."
            ),
        }
        hint = intent_hints.get(intent, "")
        if hint:
            parts.append(f"\n[Intent: {intent}] {hint}")

        if context_parts:
            parts.append("\n--- Data Context ---")
            parts.extend(context_parts)
            parts.append("--- End Context ---\n")

        if history:
            parts.append("Conversation so far:")
            for entry in history[-10:]:
                role_label = "User" if entry.role == "user" else "Assistant"
                # Truncate long prior responses to save context
                content = entry.content
                if len(content) > 500 and entry.role == "assistant":
                    content = content[:500] + "... [truncated]"
                parts.append(f"{role_label}: {content}")
            parts.append("")

        parts.append(f"User: {message}")
        return "\n".join(parts)

    async def _generate_streaming(
        self, prompt: str, history: list[ConversationEntry]
    ) -> AsyncGenerator[str, None]:
        """Stream tokens from Gemini."""
        try:
            from google import genai

            client = genai.Client()
            contents = []

            # Add conversation history as turns
            for entry in history[-10:]:
                role = "user" if entry.role == "user" else "model"
                content = entry.content
                if len(content) > 500 and entry.role == "assistant":
                    content = content[:500] + "... [truncated]"
                contents.append(
                    {"role": role, "parts": [{"text": content}]}
                )

            # Add current prompt (includes system prompt + context)
            contents.append({"role": "user", "parts": [{"text": prompt}]})

            response = await client.aio.models.generate_content_stream(
                model="gemini-3-flash-preview",
                contents=contents,
            )
            async for chunk in response:
                if chunk.text:
                    yield chunk.text
        except ImportError:
            logger.warning(
                "google-genai not available, using fallback response"
            )
            yield "I can help you understand stock analysis. "
            yield "However, the AI generation service is currently unavailable."
            yield " Please try again later."
        except Exception:
            logger.exception("Gemini streaming failed")
            raise


# ---------------------------------------------------------------------------
# API routes (unchanged — no impact on landing, compare, history pages)
# ---------------------------------------------------------------------------

def _sse_format(data: dict) -> str:
    """Format a dict as an SSE data line."""
    return f"data: {json.dumps(data)}\n\n"


@chat_router.post("")
async def chat_endpoint(body: ChatRequest, request: Request):
    """Chat with EquityIQ. Streams SSE by default, JSON if Accept: application/json."""
    chat_engine: ChatEngine = request.app.state.chat_engine

    accept = request.headers.get("accept", "")
    if "application/json" in accept and "text/event-stream" not in accept:
        response = await chat_engine.process_message_sync(body)
        return response

    async def event_stream():
        async for event in chat_engine.process_message(body):
            yield _sse_format(event)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@chat_router.get("/history/{session_id}")
async def get_chat_history(
    session_id: str,
    request: Request,
    limit: int = Query(default=50, ge=1, le=200),
) -> ChatHistoryResponse:
    """Retrieve conversation history for a chat session."""
    memory = request.app.state.vertex_memory
    if memory is None:
        return ChatHistoryResponse(session_id=session_id, messages=[])

    entries = await memory.get_conversation(session_id, limit=limit)
    return ChatHistoryResponse(session_id=session_id, messages=entries)


@chat_router.delete("/history/{session_id}")
async def delete_chat_history(session_id: str, request: Request) -> dict:
    """Clear conversation history for a chat session."""
    memory = request.app.state.vertex_memory
    if memory is not None:
        try:
            conn = await memory._get_connection()
            await conn.execute(
                "DELETE FROM conversations WHERE session_id = ?",
                (session_id,),
            )
            await conn.commit()
        except Exception:
            logger.exception(
                "Failed to delete chat history for %s", session_id
            )
    return {"deleted": True, "session_id": session_id}
