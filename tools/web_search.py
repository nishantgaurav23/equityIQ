"""Unified web search layer combining Serper + Tavily.

Provides a single interface for all web search needs across EquityIQ.
Both APIs are optional — if a key is missing, that source is skipped.
If both are available, results are merged for richer context.

Used by:
- Agent tools (PulseMonitor, ComplianceChecker, EconomyWatcher, ValuationScout)
- Chat engine (api/chat.py) for enriching conversation context
"""

from __future__ import annotations

import logging

from tools.serper_connector import serper
from tools.tavily_connector import tavily

logger = logging.getLogger(__name__)


def _truncate(text: str, max_len: int = 300) -> str:
    """Truncate text to max_len chars, appending '...' if needed."""
    if len(text) <= max_len:
        return text
    return text[:max_len].rsplit(" ", 1)[0] + "..."


async def search_stock_intelligence(
    ticker: str, company_name: str = ""
) -> dict:
    """Get comprehensive web intelligence for a stock.

    Combines Serper (Google News) + Tavily (deep research) for:
    - Latest news headlines and sentiment
    - Analyst opinions and price targets
    - Regulatory/compliance news
    - AI-generated summary (from Tavily)

    Returns:
        {
            "web_headlines": [str],     # Top news headlines
            "web_snippets": [str],      # Key snippets with context
            "analyst_info": [str],      # Analyst reports/opinions
            "web_summary": str | None,  # AI summary from Tavily
            "sources": [str],           # Source URLs
        }
    """
    result: dict = {
        "web_headlines": [],
        "web_snippets": [],
        "analyst_info": [],
        "web_summary": None,
        "sources": [],
    }

    seen_titles: set[str] = set()

    # Serper: Google News for latest headlines
    if serper.available:
        try:
            news = await serper.search_stock_news(ticker, company_name)
            for item in news.get("results", [])[:8]:
                title = item.get("title", "").strip()
                if title and title not in seen_titles:
                    seen_titles.add(title)
                    source = item.get("source", "")
                    date = item.get("date", "")
                    headline = title
                    if source:
                        headline += f" ({source})"
                    if date:
                        headline += f" [{date}]"
                    result["web_headlines"].append(headline)
                    snippet = item.get("snippet", "").strip()
                    if snippet:
                        result["web_snippets"].append(
                            _truncate(snippet)
                        )
                    link = item.get("link", "")
                    if link:
                        result["sources"].append(link)

            # Knowledge graph (stock price, company info from Google)
            kg = news.get("knowledge_graph")
            if kg and kg.get("attributes"):
                attrs = kg["attributes"]
                for k, v in attrs.items():
                    result["web_snippets"].append(f"{k}: {v}")

        except Exception:
            logger.debug("Serper stock news failed for %s", ticker)

    # Serper: Analyst reports
    if serper.available:
        try:
            analysts = await serper.search_analyst_reports(ticker)
            for item in analysts.get("results", [])[:5]:
                title = item.get("title", "").strip()
                snippet = item.get("snippet", "").strip()
                if snippet and title not in seen_titles:
                    seen_titles.add(title)
                    result["analyst_info"].append(
                        _truncate(f"{title}: {snippet}")
                    )
        except Exception:
            logger.debug("Serper analyst search failed for %s", ticker)

    # Tavily: Deep research with AI summary
    if tavily.available:
        try:
            research = await tavily.research_stock(ticker, company_name)
            if research.get("answer"):
                result["web_summary"] = research["answer"]

            for item in research.get("results", [])[:5]:
                title = item.get("title", "").strip()
                content = item.get("content", "").strip()
                if content and title not in seen_titles:
                    seen_titles.add(title)
                    result["web_snippets"].append(
                        _truncate(content)
                    )
                url = item.get("url", "")
                if url:
                    result["sources"].append(url)
        except Exception:
            logger.debug("Tavily research failed for %s", ticker)

    # Deduplicate sources
    result["sources"] = list(dict.fromkeys(result["sources"]))[:10]

    return result


async def search_regulatory_intelligence(
    ticker: str, company_name: str = ""
) -> dict:
    """Search for regulatory news, investigations, and compliance issues.

    Returns:
        {
            "regulatory_headlines": [str],
            "regulatory_details": [str],
            "web_summary": str | None,
        }
    """
    result: dict = {
        "regulatory_headlines": [],
        "regulatory_details": [],
        "web_summary": None,
    }

    if serper.available:
        try:
            data = await serper.search_regulatory_news(
                ticker, company_name
            )
            for item in data.get("results", [])[:8]:
                title = item.get("title", "").strip()
                if title:
                    result["regulatory_headlines"].append(title)
                snippet = item.get("snippet", "").strip()
                if snippet:
                    result["regulatory_details"].append(
                        _truncate(snippet)
                    )
        except Exception:
            logger.debug("Serper regulatory search failed for %s", ticker)

    if tavily.available:
        try:
            name = company_name or ticker
            data = await tavily.search(
                f"{name} ({ticker}) regulatory investigation "
                f"compliance SEBI SEC lawsuit",
                search_depth="advanced",
                max_results=5,
                topic="news",
            )
            if data.get("answer"):
                result["web_summary"] = data["answer"]
            for item in data.get("results", [])[:5]:
                content = item.get("content", "").strip()
                if content:
                    result["regulatory_details"].append(
                        _truncate(content)
                    )
        except Exception:
            logger.debug("Tavily regulatory search failed for %s", ticker)

    return result


async def search_macro_intelligence(market: str = "US") -> dict:
    """Search for macroeconomic outlook and policy news.

    Returns:
        {
            "macro_headlines": [str],
            "macro_details": [str],
            "web_summary": str | None,
        }
    """
    result: dict = {
        "macro_headlines": [],
        "macro_details": [],
        "web_summary": None,
    }

    if serper.available:
        try:
            data = await serper.search_macro_outlook(market)
            for item in data.get("results", [])[:8]:
                title = item.get("title", "").strip()
                if title:
                    result["macro_headlines"].append(title)
                snippet = item.get("snippet", "").strip()
                if snippet:
                    result["macro_details"].append(_truncate(snippet))
        except Exception:
            logger.debug("Serper macro search failed for %s", market)

    if tavily.available:
        try:
            data = await tavily.research_macro(market)
            if data.get("answer"):
                result["web_summary"] = data["answer"]
            for item in data.get("results", [])[:5]:
                content = item.get("content", "").strip()
                if content:
                    result["macro_details"].append(_truncate(content))
        except Exception:
            logger.debug("Tavily macro search failed for %s", market)

    return result


async def search_general(query: str) -> dict:
    """Search for any financial/economic topic.

    Used by the chat engine for general knowledge questions.

    Returns:
        {
            "answer": str | None,  # AI-generated answer (Tavily)
            "results": [{"title": str, "snippet": str}],
            "sources": [str],
        }
    """
    result: dict = {
        "answer": None,
        "results": [],
        "sources": [],
    }

    # Tavily first — its AI answer is the most useful for general questions
    if tavily.available:
        try:
            data = await tavily.research_topic(query)
            if data.get("answer"):
                result["answer"] = data["answer"]
            for item in data.get("results", [])[:5]:
                result["results"].append({
                    "title": item.get("title", ""),
                    "snippet": _truncate(item.get("content", "")),
                })
                url = item.get("url", "")
                if url:
                    result["sources"].append(url)
        except Exception:
            logger.debug("Tavily general search failed for: %s", query)

    # Serper as supplement
    if serper.available:
        try:
            data = await serper.search_general_finance(query)
            for item in data.get("results", [])[:5]:
                title = item.get("title", "")
                snippet = item.get("snippet", "")
                if title and not any(
                    r["title"] == title for r in result["results"]
                ):
                    result["results"].append({
                        "title": title,
                        "snippet": _truncate(snippet),
                    })
                link = item.get("link", "")
                if link:
                    result["sources"].append(link)

            # Answer box from Google
            ab = data.get("answer_box")
            if ab and not result["answer"]:
                answer = ab.get("answer") or ab.get("snippet", "")
                if answer:
                    result["answer"] = answer
        except Exception:
            logger.debug("Serper general search failed for: %s", query)

    result["sources"] = list(dict.fromkeys(result["sources"]))[:8]
    return result


def format_web_context(data: dict, section_title: str = "Web Intelligence") -> str:
    """Format web search results into a readable context string for the LLM."""
    lines: list[str] = []

    if data.get("web_summary") or data.get("answer"):
        summary = data.get("web_summary") or data.get("answer")
        lines.append(f"### {section_title} — Summary")
        lines.append(summary)
        lines.append("")

    headlines = (
        data.get("web_headlines")
        or data.get("macro_headlines")
        or data.get("regulatory_headlines")
        or []
    )
    if headlines:
        lines.append(f"### {section_title} — Headlines")
        for h in headlines[:8]:
            lines.append(f"- {h}")
        lines.append("")

    snippets = (
        data.get("web_snippets")
        or data.get("macro_details")
        or data.get("regulatory_details")
        or []
    )
    if snippets:
        lines.append(f"### {section_title} — Details")
        for s in snippets[:6]:
            lines.append(f"- {s}")
        lines.append("")

    analyst = data.get("analyst_info", [])
    if analyst:
        lines.append(f"### {section_title} — Analyst Reports")
        for a in analyst[:5]:
            lines.append(f"- {a}")
        lines.append("")

    results = data.get("results", [])
    if results and not headlines and not snippets:
        lines.append(f"### {section_title} — Search Results")
        for r in results[:6]:
            title = r.get("title", "")
            snippet = r.get("snippet", "")
            if title:
                lines.append(f"- **{title}**: {snippet}")
        lines.append("")

    return "\n".join(lines) if lines else ""
