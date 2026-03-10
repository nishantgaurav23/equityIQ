"""Tests for ComplianceChecker agent (S7.5).

Tests cover: tool functions, agent instantiation, agent card, analyze success,
analyze fallback, and ComplianceReport schema validation.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from config.data_contracts import ComplianceReport

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_sec_connector():
    """Patch the module-level _sec_connector in compliance_checker."""
    with patch("agents.compliance_checker._sec_connector") as mock:
        mock.get_sec_filings = AsyncMock(
            return_value=[
                {
                    "filing_type": "10-K",
                    "filed_date": "2025-01-15",
                    "description": "Annual report",
                    "url": "https://sec.gov/...",
                },
                {
                    "filing_type": "10-Q",
                    "filed_date": "2024-10-10",
                    "description": "Quarterly report",
                    "url": "https://sec.gov/...",
                },
            ]
        )
        mock.score_risk = AsyncMock(
            return_value={
                "latest_filing_type": "10-K",
                "days_since_filing": 30,
                "risk_flags": [],
                "risk_score": 0.1,
            }
        )
        yield mock


@pytest.fixture()
def mock_sec_error():
    """Patch _sec_connector to raise an exception."""
    with patch("agents.compliance_checker._sec_connector") as mock:
        mock.get_sec_filings = AsyncMock(side_effect=Exception("API down"))
        mock.score_risk = AsyncMock(side_effect=Exception("API down"))
        yield mock


# ---------------------------------------------------------------------------
# T1: Tool Functions -- get_sec_filings_tool
# ---------------------------------------------------------------------------


class TestGetSecFilingsTool:
    """Tests for get_sec_filings_tool."""

    @pytest.mark.asyncio
    async def test_success(self, mock_sec_connector):
        from agents.compliance_checker import get_sec_filings_tool

        result = await get_sec_filings_tool("AAPL")

        mock_sec_connector.get_sec_filings.assert_awaited_once_with("AAPL")
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["filing_type"] == "10-K"

    @pytest.mark.asyncio
    async def test_error_returns_empty(self, mock_sec_error):
        from agents.compliance_checker import get_sec_filings_tool

        result = await get_sec_filings_tool("AAPL")
        assert result == {}

    @pytest.mark.asyncio
    async def test_never_raises(self, mock_sec_error):
        from agents.compliance_checker import get_sec_filings_tool

        result = await get_sec_filings_tool("AAPL")
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# T2: Tool Functions -- score_risk_tool
# ---------------------------------------------------------------------------


class TestScoreRiskTool:
    """Tests for score_risk_tool."""

    @pytest.mark.asyncio
    async def test_success(self, mock_sec_connector):
        from agents.compliance_checker import score_risk_tool

        result = await score_risk_tool("AAPL")

        mock_sec_connector.score_risk.assert_awaited_once_with("AAPL")
        assert result["latest_filing_type"] == "10-K"
        assert result["days_since_filing"] == 30
        assert result["risk_score"] == 0.1
        assert result["risk_flags"] == []

    @pytest.mark.asyncio
    async def test_error_returns_empty(self, mock_sec_error):
        from agents.compliance_checker import score_risk_tool

        result = await score_risk_tool("AAPL")
        assert result == {}

    @pytest.mark.asyncio
    async def test_never_raises(self, mock_sec_error):
        from agents.compliance_checker import score_risk_tool

        result = await score_risk_tool("AAPL")
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# T3: Agent Class
# ---------------------------------------------------------------------------


class TestComplianceCheckerAgent:
    """Tests for ComplianceCheckerAgent instantiation and properties."""

    def test_instantiation(self):
        from agents.compliance_checker import ComplianceCheckerAgent

        agent = ComplianceCheckerAgent()
        assert agent.name == "compliance_checker"

    def test_output_schema(self):
        from agents.compliance_checker import ComplianceCheckerAgent

        agent = ComplianceCheckerAgent()
        assert agent._output_schema is ComplianceReport

    def test_inherits_base(self):
        from agents.base_agent import BaseAnalystAgent
        from agents.compliance_checker import ComplianceCheckerAgent

        assert issubclass(ComplianceCheckerAgent, BaseAnalystAgent)

    def test_has_two_tools(self):
        from agents.compliance_checker import ComplianceCheckerAgent

        agent = ComplianceCheckerAgent()
        assert len(agent._tools) == 2


# ---------------------------------------------------------------------------
# T4: Agent Card
# ---------------------------------------------------------------------------


class TestAgentCard:
    """Tests for get_agent_card()."""

    def test_card_has_name(self):
        from agents.compliance_checker import ComplianceCheckerAgent

        card = ComplianceCheckerAgent().get_agent_card()
        assert card["name"] == "compliance_checker"

    def test_card_has_output_schema(self):
        from agents.compliance_checker import ComplianceCheckerAgent

        card = ComplianceCheckerAgent().get_agent_card()
        assert card["output_schema"] == "ComplianceReport"

    def test_card_has_capabilities(self):
        from agents.compliance_checker import ComplianceCheckerAgent

        card = ComplianceCheckerAgent().get_agent_card()
        assert "get_sec_filings_tool" in card["capabilities"]
        assert "score_risk_tool" in card["capabilities"]


# ---------------------------------------------------------------------------
# T5: Module Exports
# ---------------------------------------------------------------------------


class TestModuleExports:
    """Tests for module-level exports."""

    def test_module_level_instance(self):
        from agents.compliance_checker import compliance_checker

        assert compliance_checker is not None
        assert compliance_checker.name == "compliance_checker"

    def test_factory_function(self):
        from agents.compliance_checker import create_compliance_checker

        agent = create_compliance_checker()
        assert agent.name == "compliance_checker"


# ---------------------------------------------------------------------------
# T6: Analyze Success (mocked LLM)
# ---------------------------------------------------------------------------


class TestAnalyzeSuccess:
    """Test analyze() with mocked LLM returning valid ComplianceReport."""

    @pytest.mark.asyncio
    async def test_analyze_returns_compliance_report(self):
        from agents.compliance_checker import ComplianceCheckerAgent

        report_data = ComplianceReport(
            ticker="AAPL",
            agent_name="compliance_checker",
            signal="BUY",
            confidence=0.80,
            reasoning="Clean compliance record, recent 10-K filing, no risk flags.",
            latest_filing_type="10-K",
            days_since_filing=30,
            risk_flags=[],
            risk_score=0.1,
        )

        agent = ComplianceCheckerAgent()

        mock_part = MagicMock()
        mock_part.text = report_data.model_dump_json()

        mock_event = MagicMock()
        mock_event.is_final_response.return_value = True
        mock_event.content = MagicMock()
        mock_event.content.parts = [mock_part]

        async def fake_run_async(**kwargs):
            yield mock_event

        with patch("agents.base_agent.Runner") as MockRunner:
            runner_instance = MagicMock()
            runner_instance.run_async = fake_run_async
            MockRunner.return_value = runner_instance

            with patch("agents.base_agent.InMemorySessionService") as MockSession:
                mock_session = MagicMock()
                mock_session.id = "test-session"
                MockSession.return_value.create_session = AsyncMock(return_value=mock_session)

                result = await agent.analyze("AAPL")

        assert isinstance(result, ComplianceReport)
        assert result.ticker == "AAPL"
        assert result.signal == "BUY"
        assert result.latest_filing_type == "10-K"
        assert result.days_since_filing == 30
        assert result.risk_score == 0.1
        assert result.risk_flags == []


# ---------------------------------------------------------------------------
# T7: Analyze Fallback
# ---------------------------------------------------------------------------


class TestAnalyzeFallback:
    """Test analyze() fallback on error."""

    @pytest.mark.asyncio
    async def test_fallback_on_error(self):
        from agents.compliance_checker import ComplianceCheckerAgent

        agent = ComplianceCheckerAgent()

        with (
            patch(
                "agents.base_agent.Runner",
                side_effect=Exception("LLM unavailable"),
            ),
            patch("agents.base_agent.InMemorySessionService"),
        ):
            result = await agent.analyze("AAPL")

        assert result.signal == "HOLD"
        assert result.confidence == 0.0
        assert result.ticker == "AAPL"

    @pytest.mark.asyncio
    async def test_fallback_never_raises(self):
        from agents.compliance_checker import ComplianceCheckerAgent

        agent = ComplianceCheckerAgent()

        with (
            patch(
                "agents.base_agent.Runner",
                side_effect=RuntimeError("crash"),
            ),
            patch("agents.base_agent.InMemorySessionService"),
        ):
            result = await agent.analyze("AAPL")
            assert result is not None


# ---------------------------------------------------------------------------
# T8: ComplianceReport Schema Validation
# ---------------------------------------------------------------------------


class TestComplianceReportSchema:
    """Verify ComplianceReport validates correctly for compliance scenarios."""

    def test_sell_with_going_concern(self):
        report = ComplianceReport(
            ticker="XYZ",
            agent_name="compliance_checker",
            signal="SELL",
            confidence=0.95,
            reasoning="Going concern warning detected.",
            latest_filing_type="10-K",
            days_since_filing=45,
            risk_flags=["going_concern"],
            risk_score=0.9,
        )
        assert report.signal == "SELL"
        assert "going_concern" in report.risk_flags

    def test_sell_with_restatement(self):
        report = ComplianceReport(
            ticker="XYZ",
            agent_name="compliance_checker",
            signal="SELL",
            confidence=0.90,
            reasoning="Financial restatement detected.",
            latest_filing_type="10-Q",
            days_since_filing=60,
            risk_flags=["restatement"],
            risk_score=0.85,
        )
        assert report.signal == "SELL"
        assert "restatement" in report.risk_flags

    def test_risk_score_clamped_high(self):
        report = ComplianceReport(
            ticker="XYZ",
            agent_name="compliance_checker",
            signal="SELL",
            confidence=0.80,
            reasoning="Test",
            risk_score=1.5,
        )
        assert report.risk_score == 1.0

    def test_risk_score_clamped_low(self):
        report = ComplianceReport(
            ticker="XYZ",
            agent_name="compliance_checker",
            signal="BUY",
            confidence=0.80,
            reasoning="Test",
            risk_score=-0.5,
        )
        assert report.risk_score == 0.0

    def test_confidence_clamped(self):
        report = ComplianceReport(
            ticker="XYZ",
            agent_name="compliance_checker",
            signal="HOLD",
            confidence=1.5,
            reasoning="Test",
        )
        assert report.confidence == 1.0
