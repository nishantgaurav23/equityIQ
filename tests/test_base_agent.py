"""Tests for agents/base_agent.py -- BaseAnalystAgent and create_agent factory."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from config.analyst_personas import PERSONAS
from config.data_contracts import (
    AnalystReport,
    ComplianceReport,
    EconomyReport,
    MomentumReport,
    PulseReport,
    RiskGuardianReport,
    ValuationReport,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def valuation_agent():
    from agents.base_agent import BaseAnalystAgent

    return BaseAnalystAgent(
        agent_name="valuation_scout",
        output_schema=ValuationReport,
    )


@pytest.fixture
def momentum_agent():
    from agents.base_agent import BaseAnalystAgent

    return BaseAnalystAgent(
        agent_name="momentum_tracker",
        output_schema=MomentumReport,
    )


def _dummy_tool(ticker: str) -> dict:
    """Dummy tool for testing."""
    return {"ticker": ticker, "data": "test"}


def _another_tool(value: int) -> int:
    """Another dummy tool."""
    return value * 2


# ---------------------------------------------------------------------------
# Init tests
# ---------------------------------------------------------------------------


class TestInit:
    def test_init_with_valid_persona(self, valuation_agent):
        assert valuation_agent.name == "valuation_scout"
        assert valuation_agent.persona == PERSONAS["valuation_scout"]

    def test_init_with_invalid_persona(self):
        from agents.base_agent import BaseAnalystAgent

        with pytest.raises(KeyError):
            BaseAnalystAgent(
                agent_name="nonexistent_agent",
                output_schema=AnalystReport,
            )

    def test_init_default_model(self, valuation_agent):
        assert valuation_agent.agent.model == "gemini-3-flash-preview"

    def test_init_custom_model(self):
        from agents.base_agent import BaseAnalystAgent

        agent = BaseAnalystAgent(
            agent_name="valuation_scout",
            output_schema=ValuationReport,
            model="gemini-2.0-flash",
        )
        assert agent.agent.model == "gemini-2.0-flash"

    def test_init_with_tools(self):
        from agents.base_agent import BaseAnalystAgent

        agent = BaseAnalystAgent(
            agent_name="valuation_scout",
            output_schema=ValuationReport,
            tools=[_dummy_tool, _another_tool],
        )
        assert len(agent.agent.tools) == 2

    def test_init_no_tools(self, valuation_agent):
        assert valuation_agent.agent.tools == []


# ---------------------------------------------------------------------------
# ADK Agent property tests
# ---------------------------------------------------------------------------


class TestAdkAgent:
    def test_adk_agent_created(self, valuation_agent):
        from google.adk.agents import Agent

        assert isinstance(valuation_agent.agent, Agent)

    def test_adk_agent_has_correct_instruction(self, valuation_agent):
        assert valuation_agent.agent.instruction == PERSONAS["valuation_scout"]

    def test_adk_agent_has_correct_output_schema(self, valuation_agent):
        assert valuation_agent.agent.output_schema == ValuationReport


# ---------------------------------------------------------------------------
# analyze() tests
# ---------------------------------------------------------------------------


class TestAnalyze:
    @pytest.mark.asyncio
    async def test_analyze_success(self, valuation_agent):
        """Mock Runner to return a valid ValuationReport JSON."""
        mock_report = ValuationReport(
            ticker="AAPL",
            agent_name="valuation_scout",
            signal="BUY",
            confidence=0.85,
            reasoning="Strong fundamentals",
            pe_ratio=25.5,
            pb_ratio=8.2,
        )

        with (
            patch("agents.base_agent.Runner") as MockRunner,
            patch("agents.base_agent.InMemorySessionService") as MockSessionService,
        ):
            mock_session = MagicMock()
            mock_session.id = "test-session-id"
            mock_session_service = MagicMock()
            mock_session_service.create_session = AsyncMock(return_value=mock_session)
            MockSessionService.return_value = mock_session_service

            mock_runner_instance = MagicMock()

            async def mock_run_async(*args, **kwargs):
                mock_event = MagicMock()
                mock_event.is_final_response.return_value = True
                part = MagicMock()
                part.text = mock_report.model_dump_json()
                mock_event.content = MagicMock()
                mock_event.content.parts = [part]
                yield mock_event

            mock_runner_instance.run_async = mock_run_async
            MockRunner.return_value = mock_runner_instance

            result = await valuation_agent.analyze("AAPL")

        assert isinstance(result, ValuationReport)
        assert result.ticker == "AAPL"
        assert result.signal == "BUY"
        assert result.confidence == 0.85

    @pytest.mark.asyncio
    async def test_analyze_returns_correct_schema(self, momentum_agent):
        """Momentum agent should return MomentumReport."""
        mock_report = MomentumReport(
            ticker="TSLA",
            agent_name="momentum_tracker",
            signal="SELL",
            confidence=0.70,
            reasoning="Bearish indicators",
            rsi_14=75.0,
        )

        with (
            patch("agents.base_agent.Runner") as MockRunner,
            patch("agents.base_agent.InMemorySessionService") as MockSessionService,
        ):
            mock_session = MagicMock()
            mock_session.id = "test-session-id"
            mock_session_service = MagicMock()
            mock_session_service.create_session = AsyncMock(return_value=mock_session)
            MockSessionService.return_value = mock_session_service

            mock_runner_instance = MagicMock()

            async def mock_run_async(*args, **kwargs):
                mock_event = MagicMock()
                mock_event.is_final_response.return_value = True
                part = MagicMock()
                part.text = mock_report.model_dump_json()
                mock_event.content = MagicMock()
                mock_event.content.parts = [part]
                yield mock_event

            mock_runner_instance.run_async = mock_run_async
            MockRunner.return_value = mock_runner_instance

            result = await momentum_agent.analyze("TSLA")

        assert isinstance(result, MomentumReport)
        assert result.rsi_14 == 75.0

    @pytest.mark.asyncio
    async def test_analyze_error_returns_fallback(self, valuation_agent):
        """On Runner error, return HOLD/0.0 fallback."""
        with patch("agents.base_agent.InMemorySessionService") as MockSessionService:
            mock_session = MagicMock()
            mock_session.id = "test-session-id"
            mock_session_service = MagicMock()
            mock_session_service.create_session = AsyncMock(return_value=mock_session)
            MockSessionService.return_value = mock_session_service

            with patch("agents.base_agent.Runner") as MockRunner:
                MockRunner.side_effect = Exception("LLM connection failed")
                result = await valuation_agent.analyze("AAPL")

        assert result.signal == "HOLD"
        assert result.confidence == 0.0
        assert result.ticker == "AAPL"
        assert result.agent_name == "valuation_scout"

    @pytest.mark.asyncio
    async def test_analyze_fallback_has_error_message(self, valuation_agent):
        """Fallback reasoning should contain the error message."""
        with patch("agents.base_agent.InMemorySessionService") as MockSessionService:
            mock_session = MagicMock()
            mock_session.id = "test-session-id"
            mock_session_service = MagicMock()
            mock_session_service.create_session = AsyncMock(return_value=mock_session)
            MockSessionService.return_value = mock_session_service

            with patch("agents.base_agent.Runner") as MockRunner:
                MockRunner.side_effect = ValueError("Parse error")
                result = await valuation_agent.analyze("AAPL")

        assert "Parse error" in result.reasoning

    @pytest.mark.asyncio
    async def test_analyze_never_raises(self, valuation_agent):
        """analyze() should never raise, even on unexpected errors."""
        with patch("agents.base_agent.InMemorySessionService") as MockSessionService:
            mock_session = MagicMock()
            mock_session.id = "test-session-id"
            mock_session_service = MagicMock()
            mock_session_service.create_session = AsyncMock(return_value=mock_session)
            MockSessionService.return_value = mock_session_service

            with patch("agents.base_agent.Runner") as MockRunner:
                MockRunner.side_effect = RuntimeError("Unexpected crash")
                result = await valuation_agent.analyze("AAPL")

        # Should not raise, should return fallback
        assert result.signal == "HOLD"
        assert result.confidence == 0.0


# ---------------------------------------------------------------------------
# get_agent_card() tests
# ---------------------------------------------------------------------------


class TestAgentCard:
    def test_get_agent_card_structure(self, valuation_agent):
        card = valuation_agent.get_agent_card()
        assert "name" in card
        assert "description" in card
        assert "url" in card
        assert "capabilities" in card
        assert "output_schema" in card

    def test_get_agent_card_url_from_settings(self, valuation_agent):
        card = valuation_agent.get_agent_card()
        assert card["url"] == "http://localhost:8001"

    def test_get_agent_card_capabilities(self):
        from agents.base_agent import BaseAnalystAgent

        agent = BaseAnalystAgent(
            agent_name="valuation_scout",
            output_schema=ValuationReport,
            tools=[_dummy_tool, _another_tool],
        )
        card = agent.get_agent_card()
        assert "_dummy_tool" in card["capabilities"]
        assert "_another_tool" in card["capabilities"]

    def test_get_agent_card_no_tools(self, valuation_agent):
        card = valuation_agent.get_agent_card()
        assert card["capabilities"] == []

    def test_get_agent_card_output_schema_name(self, valuation_agent):
        card = valuation_agent.get_agent_card()
        assert card["output_schema"] == "ValuationReport"

    def test_get_agent_card_name(self, valuation_agent):
        card = valuation_agent.get_agent_card()
        assert card["name"] == "valuation_scout"

    def test_get_agent_card_description(self, valuation_agent):
        card = valuation_agent.get_agent_card()
        # Description should be first sentence of persona
        assert len(card["description"]) > 0


# ---------------------------------------------------------------------------
# create_agent() factory tests
# ---------------------------------------------------------------------------


class TestCreateAgentFactory:
    def test_create_agent_factory(self):
        from agents.base_agent import create_agent

        agent = create_agent(
            agent_name="economy_watcher",
            output_schema=EconomyReport,
        )
        from agents.base_agent import BaseAnalystAgent

        assert isinstance(agent, BaseAnalystAgent)
        assert agent.name == "economy_watcher"


# ---------------------------------------------------------------------------
# All personas test
# ---------------------------------------------------------------------------


class TestAllPersonas:
    def test_all_personas_can_create_agent(self):
        from agents.base_agent import BaseAnalystAgent

        schema_map = {
            "valuation_scout": ValuationReport,
            "momentum_tracker": MomentumReport,
            "pulse_monitor": PulseReport,
            "economy_watcher": EconomyReport,
            "compliance_checker": ComplianceReport,
            "signal_synthesizer": AnalystReport,
            "risk_guardian": RiskGuardianReport,
        }
        for persona_name in PERSONAS:
            schema = schema_map.get(persona_name, AnalystReport)
            agent = BaseAnalystAgent(
                agent_name=persona_name,
                output_schema=schema,
            )
            assert agent.name == persona_name
            assert agent.persona == PERSONAS[persona_name]
