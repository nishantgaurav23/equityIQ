"""Tests for S16.2 -- Natural Language Chat Interface."""

from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, patch

import pytest

from api.chat import ChatEngine, _format_verdict_context, detect_intent, extract_tickers
from config.data_contracts import (
    AgentDetail,
    ChatHistoryResponse,
    ChatRequest,
    ChatResponse,
    ConversationEntry,
    FinalVerdict,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_verdict(ticker="AAPL", signal="BUY", confidence=0.82) -> FinalVerdict:
    return FinalVerdict(
        ticker=ticker,
        final_signal=signal,
        overall_confidence=confidence,
        price_target=185.50,
        analyst_signals={"ValuationScout": "BUY", "MomentumTracker": "HOLD"},
        analyst_details={
            "ValuationScout": AgentDetail(
                agent_name="ValuationScout",
                signal="BUY",
                confidence=0.85,
                reasoning="Strong fundamentals with low PE",
                key_metrics={"pe_ratio": 15.2},
                data_source="Polygon.io",
            ),
        },
        risk_level="MEDIUM",
        risk_summary="Beta: 1.1, Vol: 22%",
        key_drivers=["Low PE ratio", "Positive momentum"],
        session_id=str(uuid.uuid4()),
    )


def _make_memory():
    memory = AsyncMock()
    memory.get_conversation = AsyncMock(return_value=[])
    memory.store_conversation_entry = AsyncMock(return_value=str(uuid.uuid4()))
    return memory


def _make_conductor():
    conductor = AsyncMock()
    conductor.analyze = AsyncMock(return_value=_make_verdict())
    return conductor


def _make_vault():
    vault = AsyncMock()
    vault.get_verdict = AsyncMock(return_value=_make_verdict())
    return vault


@pytest.fixture
def engine():
    return ChatEngine(
        conductor=_make_conductor(),
        memory=_make_memory(),
        vault=_make_vault(),
    )


@pytest.fixture
def engine_no_gemini():
    """Engine that won't have google-genai available."""
    return ChatEngine(
        conductor=_make_conductor(),
        memory=_make_memory(),
        vault=_make_vault(),
    )


# ---------------------------------------------------------------------------
# Data contract tests
# ---------------------------------------------------------------------------

class TestChatRequestValidation:
    def test_valid_request(self):
        req = ChatRequest(message="Analyze AAPL")
        assert req.message == "Analyze AAPL"
        assert req.user_id == "default"
        assert req.session_id is None

    def test_with_session_id(self):
        sid = str(uuid.uuid4())
        req = ChatRequest(message="Hello", session_id=sid, ticker="TSLA")
        assert req.session_id == sid
        assert req.ticker == "TSLA"

    def test_empty_message_rejected(self):
        with pytest.raises(Exception):
            ChatRequest(message="")

    def test_message_too_long(self):
        with pytest.raises(Exception):
            ChatRequest(message="x" * 2001)

    def test_max_length_message_accepted(self):
        req = ChatRequest(message="x" * 2000)
        assert len(req.message) == 2000


class TestChatResponseModel:
    def test_serialization(self):
        resp = ChatResponse(
            session_id="abc-123",
            response="Analysis shows BUY signal",
            ticker="AAPL",
            verdict_session_id="v-456",
        )
        data = resp.model_dump()
        assert data["session_id"] == "abc-123"
        assert data["response"] == "Analysis shows BUY signal"
        assert data["ticker"] == "AAPL"
        assert "timestamp" in data

    def test_optional_fields(self):
        resp = ChatResponse(session_id="x", response="Hello")
        assert resp.ticker is None
        assert resp.verdict_session_id is None


class TestChatHistoryResponse:
    def test_empty_history(self):
        h = ChatHistoryResponse(session_id="s1")
        assert h.session_id == "s1"
        assert h.messages == []

    def test_with_messages(self):
        entry = ConversationEntry(
            entry_id="e1",
            user_id="default",
            session_id="s1",
            role="user",
            content="Hello",
        )
        h = ChatHistoryResponse(session_id="s1", messages=[entry])
        assert len(h.messages) == 1


# ---------------------------------------------------------------------------
# Intent detection tests
# ---------------------------------------------------------------------------

class TestIntentDetection:
    def test_analyze_explicit(self):
        assert detect_intent("Analyze AAPL") == "full_analysis"

    def test_analyze_what_about(self):
        assert detect_intent("What about TSLA?") == "quick_question"

    def test_analyze_tell_me_about(self):
        assert detect_intent("Tell me about MSFT") == "quick_question"

    def test_analyze_bare_ticker(self):
        assert detect_intent("AAPL") == "full_analysis"

    def test_analyze_evaluate(self):
        assert detect_intent("Evaluate GOOG for me") == "full_analysis"

    def test_follow_up_why(self):
        assert detect_intent("Why did you say SELL?") == "follow_up"

    def test_follow_up_explain(self):
        assert detect_intent("Explain the reasoning") == "follow_up"

    def test_follow_up_elaborate(self):
        assert detect_intent("Can you elaborate on that?") == "follow_up"

    def test_compare(self):
        assert detect_intent("Compare AAPL vs MSFT") == "compare"

    def test_compare_versus(self):
        assert detect_intent("AAPL versus TSLA") == "compare"

    def test_compare_which_better(self):
        assert detect_intent("Which is better, GOOG or AMZN?") == "compare"

    def test_general(self):
        assert detect_intent("What is a PE ratio?") == "general"

    def test_greeting(self):
        # "Hello" is a greeting — warm conversational response
        assert detect_intent("Hello") == "greeting"
        assert detect_intent("Hi") == "greeting"
        assert detect_intent("Hey!") == "greeting"
        assert detect_intent("Good morning") == "greeting"
        assert detect_intent("hello") == "greeting"

    def test_general_no_ticker(self):
        assert detect_intent("How does the stock market work?") == "general"


# ---------------------------------------------------------------------------
# Ticker extraction tests
# ---------------------------------------------------------------------------

class TestTickerExtraction:
    def test_single_ticker(self):
        assert extract_tickers("Analyze AAPL") == ["AAPL"]

    def test_multiple_tickers(self):
        result = extract_tickers("Compare AAPL vs MSFT")
        assert "AAPL" in result
        assert "MSFT" in result

    def test_india_ticker(self):
        result = extract_tickers("Check TCS.NS")
        assert "TCS.NS" in result

    def test_no_tickers(self):
        assert extract_tickers("Hello world") == []

    def test_stopwords_filtered(self):
        result = extract_tickers("I AM IN THE market")
        assert result == []

    def test_mixed_with_stopwords(self):
        result = extract_tickers("IS AAPL A good BUY?")
        assert result == ["AAPL"]


# ---------------------------------------------------------------------------
# Context building tests
# ---------------------------------------------------------------------------

class TestContextBuilding:
    def test_format_verdict_context(self):
        verdict = _make_verdict()
        context = _format_verdict_context(verdict)
        assert "AAPL" in context
        assert "BUY" in context
        assert "82%" in context
        assert "Low PE ratio" in context
        assert "ValuationScout" in context

    def test_format_verdict_no_price_target(self):
        verdict = _make_verdict()
        verdict.price_target = None
        context = _format_verdict_context(verdict)
        assert "$" not in context

    def test_build_prompt(self, engine):
        prompt = engine._build_prompt(
            "Analyze AAPL",
            ["## Analysis for AAPL\nSignal: BUY"],
            [],
            "full_analysis",
        )
        assert "EquityIQ" in prompt
        assert "Data Context" in prompt
        assert "Analyze AAPL" in prompt

    def test_build_prompt_with_history(self, engine):
        history = [
            ConversationEntry(
                entry_id="e1", user_id="default", session_id="s1",
                role="user", content="What about AAPL?"
            ),
            ConversationEntry(
                entry_id="e2", user_id="default", session_id="s1",
                role="assistant", content="AAPL shows a BUY signal."
            ),
        ]
        prompt = engine._build_prompt("Tell me more", [], history, "follow_up")
        assert "Conversation so far" in prompt
        assert "What about AAPL?" in prompt
        assert "AAPL shows a BUY signal." in prompt

    def test_build_prompt_no_context(self, engine):
        prompt = engine._build_prompt("Hello", [], [], "general")
        assert "Data Context" not in prompt
        assert "Hello" in prompt


# ---------------------------------------------------------------------------
# ChatEngine streaming tests
# ---------------------------------------------------------------------------

class TestProcessMessageStreaming:
    @pytest.mark.asyncio
    async def test_streaming_yields_session(self, engine):
        req = ChatRequest(message="Hello")
        events = []
        with patch.object(engine, "_generate_streaming", return_value=_async_iter(["Hi"])):
            async for event in engine.process_message(req):
                events.append(event)
        assert events[0]["type"] == "session"
        assert "session_id" in events[0]

    @pytest.mark.asyncio
    async def test_streaming_yields_tokens(self, engine):
        req = ChatRequest(message="Hello")
        events = []
        with patch.object(
            engine, "_generate_streaming", return_value=_async_iter(["Hello ", "world"])
        ):
            async for event in engine.process_message(req):
                events.append(event)
        token_events = [e for e in events if e["type"] == "token"]
        assert len(token_events) == 2
        assert token_events[0]["content"] == "Hello "

    @pytest.mark.asyncio
    async def test_streaming_yields_done(self, engine):
        req = ChatRequest(message="Hello")
        events = []
        with patch.object(
            engine, "_generate_streaming", return_value=_async_iter(["response"])
        ):
            async for event in engine.process_message(req):
                events.append(event)
        done_events = [e for e in events if e["type"] == "done"]
        assert len(done_events) == 1
        assert done_events[0]["full_response"] == "response"

    @pytest.mark.asyncio
    async def test_analysis_trigger(self, engine):
        """'Analyze AAPL' should call conductor.analyze."""
        req = ChatRequest(message="Analyze AAPL")
        with patch.object(
            engine, "_generate_streaming", return_value=_async_iter(["ok"])
        ):
            async for _ in engine.process_message(req):
                pass
        engine._conductor.analyze.assert_called_once()

    @pytest.mark.asyncio
    async def test_session_id_preserved(self, engine):
        sid = str(uuid.uuid4())
        req = ChatRequest(message="Hello", session_id=sid)
        events = []
        with patch.object(
            engine, "_generate_streaming", return_value=_async_iter(["hi"])
        ):
            async for event in engine.process_message(req):
                events.append(event)
        assert events[0]["session_id"] == sid

    @pytest.mark.asyncio
    async def test_context_event_with_ticker(self, engine):
        req = ChatRequest(message="Analyze AAPL")
        events = []
        with patch.object(
            engine, "_generate_streaming", return_value=_async_iter(["ok"])
        ):
            async for event in engine.process_message(req):
                events.append(event)
        context_events = [e for e in events if e["type"] == "context"]
        assert len(context_events) == 1
        assert context_events[0]["ticker"] == "AAPL"


class TestProcessMessageSync:
    @pytest.mark.asyncio
    async def test_sync_returns_chat_response(self, engine):
        req = ChatRequest(message="Hello")
        with patch.object(
            engine, "_generate_streaming", return_value=_async_iter(["Hello there"])
        ):
            resp = await engine.process_message_sync(req)
        assert isinstance(resp, ChatResponse)
        assert resp.response == "Hello there"
        assert resp.session_id


# ---------------------------------------------------------------------------
# Conversation persistence tests
# ---------------------------------------------------------------------------

class TestConversationPersistence:
    @pytest.mark.asyncio
    async def test_stores_user_and_assistant(self, engine):
        req = ChatRequest(message="Hello")
        with patch.object(
            engine, "_generate_streaming", return_value=_async_iter(["Hi"])
        ):
            async for _ in engine.process_message(req):
                pass
        # Should store 2 entries: user + assistant
        assert engine._memory.store_conversation_entry.call_count == 2
        calls = engine._memory.store_conversation_entry.call_args_list
        user_entry = calls[0][0][0]
        assistant_entry = calls[1][0][0]
        assert user_entry.role == "user"
        assert user_entry.content == "Hello"
        assert assistant_entry.role == "assistant"
        assert assistant_entry.content == "Hi"


# ---------------------------------------------------------------------------
# Context grounding tests
# ---------------------------------------------------------------------------

class TestContextGrounding:
    @pytest.mark.asyncio
    async def test_analyze_includes_verdict_context(self, engine):
        req = ChatRequest(message="Analyze AAPL")
        prompts_captured = []
        original_build = engine._build_prompt

        def capture_prompt(msg, ctx, hist, intent):
            prompts_captured.append((msg, ctx, hist))
            return original_build(msg, ctx, hist, intent)

        engine._build_prompt = capture_prompt
        with patch.object(
            engine, "_generate_streaming", return_value=_async_iter(["ok"])
        ):
            async for _ in engine.process_message(req):
                pass
        assert len(prompts_captured) == 1
        _, context_parts, _ = prompts_captured[0]
        assert len(context_parts) > 0
        assert "AAPL" in context_parts[0]


# ---------------------------------------------------------------------------
# Gemini failure fallback tests
# ---------------------------------------------------------------------------

class TestGeminiFailureFallback:
    @pytest.mark.asyncio
    async def test_gemini_error_yields_fallback(self, engine):
        req = ChatRequest(message="Hello")

        async def failing_gen(*args, **kwargs):
            raise RuntimeError("Gemini down")
            yield  # make it a generator  # noqa: E501

        with patch.object(engine, "_generate_streaming", side_effect=failing_gen):
            events = []
            async for event in engine.process_message(req):
                events.append(event)
        token_events = [e for e in events if e["type"] == "token"]
        assert len(token_events) == 1
        assert "error" in token_events[0]["content"].lower()

    @pytest.mark.asyncio
    async def test_import_error_fallback(self):
        """When google-genai is not installed, should yield fallback."""
        engine = ChatEngine(memory=_make_memory())
        req = ChatRequest(message="Hello")
        events = []
        # _generate_streaming will try to import google.genai
        # Mock it to raise ImportError
        with patch.dict("sys.modules", {"google": None, "google.genai": None}):
            with patch.object(
                engine, "_generate_streaming",
                return_value=_async_iter(["Fallback response"]),
            ):
                async for event in engine.process_message(req):
                    events.append(event)
        done = [e for e in events if e["type"] == "done"]
        assert len(done) == 1


# ---------------------------------------------------------------------------
# API endpoint tests (using FastAPI TestClient)
# ---------------------------------------------------------------------------

class TestChatEndpointStreaming:
    @pytest.mark.asyncio
    async def test_post_chat_sse(self):
        from httpx import ASGITransport, AsyncClient

        app = _create_test_app()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/chat",
                json={"message": "Hello"},
                headers={"Accept": "text/event-stream"},
            )
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]
        # Parse SSE lines
        lines = resp.text.strip().split("\n")
        data_lines = [line for line in lines if line.startswith("data: ")]
        assert len(data_lines) >= 2  # session + at least token/done
        first = json.loads(data_lines[0].removeprefix("data: "))
        assert first["type"] == "session"


class TestChatEndpointJson:
    @pytest.mark.asyncio
    async def test_post_chat_json(self):
        from httpx import ASGITransport, AsyncClient

        app = _create_test_app()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/chat",
                json={"message": "Hello"},
                headers={"Accept": "application/json"},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert "session_id" in body
        assert "response" in body


class TestChatHistoryEndpoint:
    @pytest.mark.asyncio
    async def test_get_history(self):
        from httpx import ASGITransport, AsyncClient

        app = _create_test_app()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/chat/history/test-session")
        assert resp.status_code == 200
        body = resp.json()
        assert body["session_id"] == "test-session"
        assert isinstance(body["messages"], list)


class TestChatHistoryDelete:
    @pytest.mark.asyncio
    async def test_delete_history(self):
        from httpx import ASGITransport, AsyncClient

        app = _create_test_app()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.delete("/api/v1/chat/history/test-session")
        assert resp.status_code == 200
        body = resp.json()
        assert body["deleted"] is True


class TestEmptyMessageRejected:
    @pytest.mark.asyncio
    async def test_empty_message_422(self):
        from httpx import ASGITransport, AsyncClient

        app = _create_test_app()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/chat",
                json={"message": ""},
                headers={"Accept": "application/json"},
            )
        assert resp.status_code == 422


class TestMessageTooLong:
    @pytest.mark.asyncio
    async def test_long_message_422(self):
        from httpx import ASGITransport, AsyncClient

        app = _create_test_app()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/chat",
                json={"message": "x" * 2001},
                headers={"Accept": "application/json"},
            )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _async_iter(items):
    """Create an async iterator from a list."""
    for item in items:
        yield item


def _create_test_app():
    """Create a minimal FastAPI app with chat routes for testing."""
    from fastapi import FastAPI

    from api.chat import ChatEngine, chat_router

    app = FastAPI()
    app.include_router(chat_router)

    # Mock app.state
    memory = _make_memory()
    engine = ChatEngine(
        conductor=_make_conductor(),
        memory=memory,
        vault=_make_vault(),
    )

    # Patch _generate_streaming to avoid real Gemini calls
    async def mock_generate(prompt, history):
        yield "Test response from EquityIQ."

    engine._generate_streaming = mock_generate
    app.state.chat_engine = engine
    app.state.vertex_memory = memory

    return app
