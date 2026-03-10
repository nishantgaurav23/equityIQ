"""Chat engine and API routes for natural language chat interface (S16.2)."""

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

# Ticker pattern: 1-5 uppercase letters, optionally with .NS/.BO suffix for India
_TICKER_PATTERN = re.compile(r"\b([A-Z]{1,5}(?:\.(?:NS|BO))?)\b")

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
}

_SYSTEM_PROMPT = """You are EquityIQ, an AI stock analysis assistant. You help users understand \
stock analysis results from our multi-agent system.

Rules:
- Always ground your answers in the analysis data provided in the context
- Never give specific buy/sell financial advice -- present the analysis findings objectively
- If asked about a ticker not yet analyzed, offer to run an analysis
- Be concise but thorough in explanations
- Reference specific agent findings when explaining signals (e.g. ValuationScout, MomentumTracker)
- Acknowledge uncertainty when data is limited
- Use plain language, avoid excessive jargon
"""


def detect_intent(message: str) -> str:
    """Classify user message intent.

    Returns one of: 'analyze', 'follow_up', 'compare', 'general'.
    """
    lower = message.lower().strip()

    # Compare intent: "compare X vs Y", "X versus Y", "which is better"
    if any(kw in lower for kw in ["compare", " vs ", " versus ", "which is better"]):
        return "compare"

    # Analyze intent: explicit analysis request
    analyze_keywords = [
        "analyze", "analysis", "analyse", "what do you think about",
        "how is", "how does", "look at", "check out", "evaluate",
        "tell me about", "what about",
    ]
    if any(kw in lower for kw in analyze_keywords):
        tickers = extract_tickers(message)
        if tickers:
            return "analyze"

    # Follow-up intent: references prior context
    follow_up_keywords = [
        "why did you", "why is it", "explain", "what made you",
        "tell me more", "elaborate", "go deeper", "can you clarify",
        "what does that mean", "why sell", "why buy", "why hold",
        "reason for", "reasoning behind",
    ]
    if any(kw in lower for kw in follow_up_keywords):
        return "follow_up"

    # Check for bare ticker mentions that imply analysis
    tickers = extract_tickers(message)
    if tickers and len(lower.split()) <= 5:
        return "analyze"

    return "general"


def extract_tickers(message: str) -> list[str]:
    """Extract potential stock ticker symbols from a message."""
    found = _TICKER_PATTERN.findall(message)
    return [t for t in found if t not in _TICKER_STOPWORDS]


def _format_verdict_context(verdict: FinalVerdict) -> str:
    """Format a FinalVerdict into readable context for the LLM prompt."""
    lines = [
        f"## Analysis for {verdict.ticker}",
        f"Signal: {verdict.final_signal} (confidence: {verdict.overall_confidence:.0%})",
        f"Risk Level: {verdict.risk_level}",
    ]
    if verdict.price_target:
        lines.append(f"Price Target: ${verdict.price_target:.2f}")
    if verdict.risk_summary:
        lines.append(f"Risk Summary: {verdict.risk_summary}")
    if verdict.key_drivers:
        lines.append("Key Drivers:")
        for driver in verdict.key_drivers:
            lines.append(f"  - {driver}")
    if verdict.analyst_details:
        lines.append("\nAgent Reports:")
        for name, detail in verdict.analyst_details.items():
            lines.append(
                f"  {name}: {detail.signal} ({detail.confidence:.0%}) -- {detail.reasoning}"
            )
    return "\n".join(lines)


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
        ticker = request.ticker or (tickers[0] if tickers else None)
        verdict_session_id = None

        # Build context
        context_parts = []
        history_entries = []

        # Retrieve conversation history
        if self._memory:
            try:
                history_entries = await self._memory.get_conversation(
                    session_id, limit=20
                )
            except Exception:
                logger.exception("Failed to retrieve conversation history")

        # Handle analyze intent -- trigger actual analysis
        if intent == "analyze" and ticker and self._conductor:
            try:
                verdict = await asyncio.wait_for(
                    self._conductor.analyze(ticker), timeout=60
                )
                context_parts.append(_format_verdict_context(verdict))
                verdict_session_id = verdict.session_id
            except Exception:
                logger.exception("Analysis failed for %s", ticker)
                context_parts.append(
                    f"Note: Analysis for {ticker} failed. Respond based on general knowledge."
                )

        # Handle compare intent
        elif intent == "compare" and len(tickers) >= 2 and self._conductor:
            for t in tickers[:3]:
                try:
                    v = await asyncio.wait_for(
                        self._conductor.analyze(t), timeout=60
                    )
                    context_parts.append(_format_verdict_context(v))
                    if not verdict_session_id:
                        verdict_session_id = v.session_id
                except Exception:
                    logger.exception("Comparison analysis failed for %s", t)

        # Handle follow_up -- use recent verdict from vault
        elif intent == "follow_up" and self._vault:
            if ticker:
                try:
                    from memory.history_retriever import HistoryRetriever

                    retriever = HistoryRetriever(self._vault)
                    verdicts = await retriever.get_ticker_history(ticker, limit=1)
                    if verdicts:
                        context_parts.append(_format_verdict_context(verdicts[0]))
                        verdict_session_id = verdicts[0].session_id
                except Exception:
                    logger.exception("Failed to retrieve history for follow-up")
            # Also check last conversation entry for context ticker
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
                            verdict_session_id = last_with_ticker.verdict_session_id
                    except Exception:
                        pass

        # Build LLM prompt
        prompt = self._build_prompt(
            request.message, context_parts, history_entries
        )

        # Generate response via Gemini
        full_response = ""
        try:
            async for token in self._generate_streaming(prompt, history_entries):
                full_response += token
                yield {"type": "token", "content": token}
        except Exception:
            logger.exception("Gemini generation failed")
            full_response = (
                "I'm sorry, I encountered an error generating a response. "
                "Please try again."
            )
            yield {"type": "token", "content": full_response}

        # Send context event if we have ticker info
        if ticker:
            yield {
                "type": "context",
                "ticker": ticker,
                "verdict_session_id": verdict_session_id,
            }

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
    ) -> str:
        """Build the full prompt with system instructions, context, and message."""
        parts = [_SYSTEM_PROMPT]

        if context_parts:
            parts.append("\n--- Analysis Context ---")
            parts.extend(context_parts)
            parts.append("--- End Context ---\n")

        if history:
            parts.append("Previous conversation:")
            for entry in history[-10:]:
                role_label = "User" if entry.role == "user" else "Assistant"
                parts.append(f"{role_label}: {entry.content}")
            parts.append("")

        parts.append(f"User: {message}")
        return "\n".join(parts)

    async def _generate_streaming(
        self, prompt: str, history: list[ConversationEntry]
    ) -> AsyncGenerator[str, None]:
        """Stream tokens from Gemini. Falls back to a simple response on import error."""
        try:
            from google import genai

            client = genai.Client()
            contents = []

            # Add history as conversation turns
            for entry in history[-10:]:
                role = "user" if entry.role == "user" else "model"
                contents.append({"role": role, "parts": [{"text": entry.content}]})

            # Add current prompt
            contents.append({"role": "user", "parts": [{"text": prompt}]})

            response = await client.aio.models.generate_content_stream(
                model="gemini-2.0-flash",
                contents=contents,
            )
            async for chunk in response:
                if chunk.text:
                    yield chunk.text
        except ImportError:
            logger.warning("google-genai not available, using fallback response")
            yield "I can help you understand stock analysis. "
            yield "However, the AI generation service is currently unavailable. "
            yield "Please try again later."
        except Exception:
            logger.exception("Gemini streaming failed")
            raise


def _sse_format(data: dict) -> str:
    """Format a dict as an SSE data line."""
    return f"data: {json.dumps(data)}\n\n"


@chat_router.post("")
async def chat_endpoint(body: ChatRequest, request: Request):
    """Chat with EquityIQ. Streams SSE by default, JSON if Accept: application/json."""
    chat_engine: ChatEngine = request.app.state.chat_engine

    # JSON response mode
    accept = request.headers.get("accept", "")
    if "application/json" in accept and "text/event-stream" not in accept:
        response = await chat_engine.process_message_sync(body)
        return response

    # SSE streaming mode
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
                "DELETE FROM conversations WHERE session_id = ?", (session_id,)
            )
            await conn.commit()
        except Exception:
            logger.exception("Failed to delete chat history for %s", session_id)
    return {"deleted": True, "session_id": session_id}
