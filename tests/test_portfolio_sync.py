"""Tests for S17.3 -- Portfolio Sync from Brokers.

Validates unified import, analysis, side-by-side comparison,
background scheduler, and full sync flow.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

from config.data_contracts import FinalVerdict, PortfolioInsight
from integrations.alpaca import AlpacaAccount, AlpacaPortfolio, AlpacaPosition
from integrations.zerodha import ZerodhaHolding, ZerodhaPortfolio

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_zerodha_portfolio(
    holdings: list[dict] | None = None,
) -> ZerodhaPortfolio:
    """Build a ZerodhaPortfolio for testing."""
    if holdings is None:
        holdings = [
            {
                "tradingsymbol": "RELIANCE",
                "exchange": "NSE",
                "quantity": 10,
                "average_price": 2400.0,
                "last_price": 2500.0,
                "pnl": 1000.0,
                "equityiq_ticker": "RELIANCE.NS",
            },
            {
                "tradingsymbol": "TCS",
                "exchange": "NSE",
                "quantity": 5,
                "average_price": 3500.0,
                "last_price": 3600.0,
                "pnl": 500.0,
                "equityiq_ticker": "TCS.NS",
            },
        ]
    holding_objs = [ZerodhaHolding(**h) for h in holdings]
    total_invested = sum(h.average_price * h.quantity for h in holding_objs)
    current_value = sum(h.last_price * h.quantity for h in holding_objs)
    total_pnl = sum(h.pnl for h in holding_objs)
    tickers = sorted({h.equityiq_ticker for h in holding_objs if h.equityiq_ticker})
    return ZerodhaPortfolio(
        holdings=holding_objs,
        positions=[],
        total_invested=total_invested,
        current_value=current_value,
        total_pnl=total_pnl,
        total_pnl_percentage=(total_pnl / total_invested * 100) if total_invested > 0 else 0.0,
        day_pnl=0.0,
        equityiq_tickers=tickers,
    )


def _make_alpaca_portfolio(
    positions: list[dict] | None = None,
) -> AlpacaPortfolio:
    """Build an AlpacaPortfolio for testing."""
    if positions is None:
        positions = [
            {
                "symbol": "AAPL",
                "qty": 20.0,
                "avg_entry_price": 170.0,
                "current_price": 180.0,
                "market_value": 3600.0,
                "unrealized_pl": 200.0,
                "unrealized_plpc": 0.0588,
                "side": "long",
                "equityiq_ticker": "AAPL",
            },
            {
                "symbol": "GOOGL",
                "qty": 10.0,
                "avg_entry_price": 140.0,
                "current_price": 145.0,
                "market_value": 1450.0,
                "unrealized_pl": 50.0,
                "unrealized_plpc": 0.0357,
                "side": "long",
                "equityiq_ticker": "GOOGL",
            },
        ]
    pos_objs = [AlpacaPosition(**p) for p in positions]
    account = AlpacaAccount(
        account_id="test-account",
        buying_power=50000.0,
        portfolio_value=55000.0,
        cash=50000.0,
        equity=55000.0,
        last_equity=54000.0,
        day_trade_count=0,
        pattern_day_trader=False,
        trading_blocked=False,
        account_blocked=False,
    )
    tickers = sorted({p.equityiq_ticker for p in pos_objs if p.equityiq_ticker})
    return AlpacaPortfolio(
        positions=pos_objs,
        account=account,
        portfolio_value=55000.0,
        buying_power=50000.0,
        total_unrealized_pl=sum(p.unrealized_pl for p in pos_objs),
        total_unrealized_plpc=0.05,
        day_pl=1000.0,
        equityiq_tickers=tickers,
    )


def _make_portfolio_insight(tickers: list[str]) -> PortfolioInsight:
    """Build a PortfolioInsight with verdicts for given tickers."""
    verdicts = []
    signals = ["BUY", "SELL", "HOLD", "STRONG_BUY", "STRONG_SELL"]
    for i, ticker in enumerate(tickers):
        signal = signals[i % len(signals)]
        verdicts.append(
            FinalVerdict(
                ticker=ticker,
                final_signal=signal,
                overall_confidence=0.72,
                analyst_signals={"valuation_scout": signal},
                risk_summary="moderate risk",
                key_drivers=["test driver"],
                session_id=f"session-{i}",
            )
        )
    return PortfolioInsight(
        tickers=tickers,
        verdicts=verdicts,
        portfolio_signal="HOLD",
        diversification_score=0.6,
        top_pick=tickers[0] if tickers else None,
    )


# ---------------------------------------------------------------------------
# Model Tests
# ---------------------------------------------------------------------------

class TestUnifiedModels:
    """Test UnifiedHolding and related Pydantic models."""

    def test_unified_holding_model(self):
        from integrations.portfolio_sync import UnifiedHolding

        h = UnifiedHolding(
            ticker="AAPL",
            quantity=10.0,
            avg_price=170.0,
            current_price=180.0,
            unrealized_pnl=100.0,
            broker_source="alpaca",
        )
        assert h.ticker == "AAPL"
        assert h.broker_source == "alpaca"
        assert h.unrealized_pnl == 100.0

    def test_unified_portfolio_model(self):
        from integrations.portfolio_sync import UnifiedHolding, UnifiedPortfolio

        h = UnifiedHolding(
            ticker="AAPL",
            quantity=10.0,
            avg_price=170.0,
            current_price=180.0,
            unrealized_pnl=100.0,
            broker_source="alpaca",
        )
        port = UnifiedPortfolio(holdings=[h])
        assert len(port.holdings) == 1
        assert port.errors == []

    def test_holding_comparison_model(self):
        from integrations.portfolio_sync import HoldingComparison

        c = HoldingComparison(
            ticker="AAPL",
            broker_source="alpaca",
            quantity=10.0,
            avg_price=170.0,
            current_price=180.0,
            unrealized_pnl=100.0,
            equityiq_signal="BUY",
            equityiq_confidence=0.72,
            action_hint="HOLD aligns",
        )
        assert c.equityiq_signal == "BUY"
        assert c.action_hint == "HOLD aligns"

    def test_sync_report_model(self):
        from integrations.portfolio_sync import SyncReport

        report = SyncReport(
            comparisons=[],
            total_holdings=0,
            analyzed_count=0,
        )
        assert report.total_holdings == 0
        assert report.sync_errors == []


# ---------------------------------------------------------------------------
# Import Tests (FR-1)
# ---------------------------------------------------------------------------

class TestImportHoldings:
    """FR-1: Unified portfolio import from brokers."""

    async def test_import_zerodha_only(self):
        from integrations.portfolio_sync import PortfolioSyncer

        zerodha_client = AsyncMock()
        zerodha_client.get_portfolio_summary = AsyncMock(
            return_value=_make_zerodha_portfolio()
        )

        syncer = PortfolioSyncer(
            zerodha_client=zerodha_client,
            alpaca_client=None,
            conductor=AsyncMock(),
        )
        portfolio = await syncer.import_holdings(brokers="zerodha")
        assert len(portfolio.holdings) == 2
        assert all(h.broker_source == "zerodha" for h in portfolio.holdings)
        assert portfolio.holdings[0].ticker == "RELIANCE.NS"

    async def test_import_alpaca_only(self):
        from integrations.portfolio_sync import PortfolioSyncer

        alpaca_client = AsyncMock()
        alpaca_client.get_portfolio_summary = AsyncMock(
            return_value=_make_alpaca_portfolio()
        )

        syncer = PortfolioSyncer(
            zerodha_client=None,
            alpaca_client=alpaca_client,
            conductor=AsyncMock(),
        )
        portfolio = await syncer.import_holdings(brokers="alpaca")
        assert len(portfolio.holdings) == 2
        assert all(h.broker_source == "alpaca" for h in portfolio.holdings)
        assert portfolio.holdings[0].ticker == "AAPL"

    async def test_import_both_brokers(self):
        from integrations.portfolio_sync import PortfolioSyncer

        zerodha_client = AsyncMock()
        zerodha_client.get_portfolio_summary = AsyncMock(
            return_value=_make_zerodha_portfolio()
        )
        alpaca_client = AsyncMock()
        alpaca_client.get_portfolio_summary = AsyncMock(
            return_value=_make_alpaca_portfolio()
        )

        syncer = PortfolioSyncer(
            zerodha_client=zerodha_client,
            alpaca_client=alpaca_client,
            conductor=AsyncMock(),
        )
        portfolio = await syncer.import_holdings(brokers="all")
        assert len(portfolio.holdings) == 4  # 2 Zerodha + 2 Alpaca
        sources = {h.broker_source for h in portfolio.holdings}
        assert sources == {"zerodha", "alpaca"}

    async def test_import_broker_failure_graceful(self):
        from integrations.portfolio_sync import PortfolioSyncer

        zerodha_client = AsyncMock()
        zerodha_client.get_portfolio_summary = AsyncMock(side_effect=Exception("Zerodha down"))
        alpaca_client = AsyncMock()
        alpaca_client.get_portfolio_summary = AsyncMock(
            return_value=_make_alpaca_portfolio()
        )

        syncer = PortfolioSyncer(
            zerodha_client=zerodha_client,
            alpaca_client=alpaca_client,
            conductor=AsyncMock(),
        )
        portfolio = await syncer.import_holdings(brokers="all")
        assert len(portfolio.holdings) == 2  # Only Alpaca
        assert len(portfolio.errors) == 1
        assert "zerodha" in portfolio.errors[0].lower()

    async def test_import_both_fail(self):
        from integrations.portfolio_sync import PortfolioSyncer

        zerodha_client = AsyncMock()
        zerodha_client.get_portfolio_summary = AsyncMock(side_effect=Exception("down"))
        alpaca_client = AsyncMock()
        alpaca_client.get_portfolio_summary = AsyncMock(side_effect=Exception("down"))

        syncer = PortfolioSyncer(
            zerodha_client=zerodha_client,
            alpaca_client=alpaca_client,
            conductor=AsyncMock(),
        )
        portfolio = await syncer.import_holdings(brokers="all")
        assert len(portfolio.holdings) == 0
        assert len(portfolio.errors) == 2

    async def test_import_no_client_for_requested_broker(self):
        from integrations.portfolio_sync import PortfolioSyncer

        syncer = PortfolioSyncer(
            zerodha_client=None,
            alpaca_client=None,
            conductor=AsyncMock(),
        )
        portfolio = await syncer.import_holdings(brokers="all")
        assert len(portfolio.holdings) == 0


# ---------------------------------------------------------------------------
# Analysis Tests (FR-2)
# ---------------------------------------------------------------------------

class TestRunAnalysis:
    """FR-2: Run analysis on imported tickers."""

    async def test_run_analysis_on_tickers(self):
        from integrations.portfolio_sync import PortfolioSyncer, UnifiedHolding, UnifiedPortfolio

        conductor = AsyncMock()
        insight = _make_portfolio_insight(["AAPL", "GOOGL"])
        conductor.analyze_portfolio = AsyncMock(return_value=insight)

        syncer = PortfolioSyncer(
            zerodha_client=None, alpaca_client=None, conductor=conductor
        )
        portfolio = UnifiedPortfolio(
            holdings=[
                UnifiedHolding(
                    ticker="AAPL", quantity=10, avg_price=170.0,
                    current_price=180.0, unrealized_pnl=100.0, broker_source="alpaca",
                ),
                UnifiedHolding(
                    ticker="GOOGL", quantity=5, avg_price=140.0,
                    current_price=145.0, unrealized_pnl=25.0, broker_source="alpaca",
                ),
            ]
        )
        result = await syncer.run_analysis(portfolio)
        assert result is not None
        conductor.analyze_portfolio.assert_called_once()
        call_tickers = conductor.analyze_portfolio.call_args[0][0]
        assert sorted(call_tickers) == ["AAPL", "GOOGL"]

    async def test_run_analysis_empty_portfolio(self):
        from integrations.portfolio_sync import PortfolioSyncer, UnifiedPortfolio

        syncer = PortfolioSyncer(
            zerodha_client=None, alpaca_client=None, conductor=AsyncMock()
        )
        portfolio = UnifiedPortfolio(holdings=[])
        result = await syncer.run_analysis(portfolio)
        assert result is None

    async def test_run_analysis_batching(self):
        from integrations.portfolio_sync import PortfolioSyncer, UnifiedHolding, UnifiedPortfolio

        # Create 15 unique tickers
        holdings = []
        for i in range(15):
            ticker = f"TICK{i}"
            holdings.append(
                UnifiedHolding(
                    ticker=ticker, quantity=1, avg_price=100.0,
                    current_price=100.0, unrealized_pnl=0.0, broker_source="alpaca",
                )
            )
        portfolio = UnifiedPortfolio(holdings=holdings)

        # Mock conductor to return insights for whatever tickers are passed
        conductor = AsyncMock()

        async def mock_analyze(tickers, session_id=None):
            return _make_portfolio_insight(tickers)

        conductor.analyze_portfolio = AsyncMock(side_effect=mock_analyze)

        syncer = PortfolioSyncer(
            zerodha_client=None, alpaca_client=None, conductor=conductor
        )
        result = await syncer.run_analysis(portfolio)
        assert result is not None
        # Should have been called twice: batch of 10 + batch of 5
        assert conductor.analyze_portfolio.call_count == 2

    async def test_run_analysis_deduplicates_tickers(self):
        from integrations.portfolio_sync import PortfolioSyncer, UnifiedHolding, UnifiedPortfolio

        conductor = AsyncMock()
        conductor.analyze_portfolio = AsyncMock(
            return_value=_make_portfolio_insight(["AAPL"])
        )

        # Same ticker from two brokers
        holdings = [
            UnifiedHolding(
                ticker="AAPL", quantity=10, avg_price=170.0,
                current_price=180.0, unrealized_pnl=100.0, broker_source="alpaca",
            ),
            UnifiedHolding(
                ticker="AAPL", quantity=5, avg_price=175.0,
                current_price=180.0, unrealized_pnl=25.0, broker_source="zerodha",
            ),
        ]
        portfolio = UnifiedPortfolio(holdings=holdings)

        syncer = PortfolioSyncer(
            zerodha_client=None, alpaca_client=None, conductor=conductor
        )
        await syncer.run_analysis(portfolio)
        call_tickers = conductor.analyze_portfolio.call_args[0][0]
        assert call_tickers == ["AAPL"]  # Deduplicated


# ---------------------------------------------------------------------------
# Comparison Tests (FR-3)
# ---------------------------------------------------------------------------

class TestComparison:
    """FR-3: Side-by-side comparison."""

    async def test_comparison_report(self):
        from integrations.portfolio_sync import PortfolioSyncer, UnifiedHolding, UnifiedPortfolio

        syncer = PortfolioSyncer(
            zerodha_client=None, alpaca_client=None, conductor=AsyncMock()
        )
        portfolio = UnifiedPortfolio(
            holdings=[
                UnifiedHolding(
                    ticker="AAPL", quantity=10, avg_price=170.0,
                    current_price=180.0, unrealized_pnl=100.0, broker_source="alpaca",
                ),
            ]
        )
        insight = _make_portfolio_insight(["AAPL"])
        report = syncer.get_comparison(portfolio, insight)
        assert len(report.comparisons) == 1
        assert report.comparisons[0].ticker == "AAPL"
        assert report.comparisons[0].equityiq_signal == "BUY"
        assert report.total_holdings == 1
        assert report.analyzed_count == 1

    async def test_comparison_action_hints_buy_on_held(self):
        from integrations.portfolio_sync import PortfolioSyncer, UnifiedHolding, UnifiedPortfolio

        syncer = PortfolioSyncer(
            zerodha_client=None, alpaca_client=None, conductor=AsyncMock()
        )
        portfolio = UnifiedPortfolio(
            holdings=[
                UnifiedHolding(
                    ticker="AAPL", quantity=10, avg_price=170.0,
                    current_price=180.0, unrealized_pnl=100.0, broker_source="alpaca",
                ),
            ]
        )
        # BUY signal on held stock
        insight = _make_portfolio_insight(["AAPL"])
        report = syncer.get_comparison(portfolio, insight)
        hint = report.comparisons[0].action_hint
        assert "add" in hint.lower() or "aligns" in hint.lower()

    async def test_comparison_action_hints_sell(self):
        from integrations.portfolio_sync import PortfolioSyncer, UnifiedHolding, UnifiedPortfolio

        syncer = PortfolioSyncer(
            zerodha_client=None, alpaca_client=None, conductor=AsyncMock()
        )
        portfolio = UnifiedPortfolio(
            holdings=[
                UnifiedHolding(
                    ticker="SELL_STOCK", quantity=10, avg_price=100.0,
                    current_price=90.0, unrealized_pnl=-100.0, broker_source="alpaca",
                ),
            ]
        )
        # Force a SELL signal
        verdicts = [
            FinalVerdict(
                ticker="SELL_STOCK",
                final_signal="SELL",
                overall_confidence=0.72,
                analyst_signals={"valuation_scout": "SELL"},
                risk_summary="high risk",
                key_drivers=["declining"],
                session_id="s1",
            )
        ]
        insight = PortfolioInsight(
            tickers=["SELL_STOCK"],
            verdicts=verdicts,
            portfolio_signal="SELL",
            diversification_score=0.3,
        )
        report = syncer.get_comparison(portfolio, insight)
        assert "sell" in report.comparisons[0].action_hint.lower()

    async def test_comparison_hold_signal(self):
        from integrations.portfolio_sync import PortfolioSyncer, UnifiedHolding, UnifiedPortfolio

        syncer = PortfolioSyncer(
            zerodha_client=None, alpaca_client=None, conductor=AsyncMock()
        )
        portfolio = UnifiedPortfolio(
            holdings=[
                UnifiedHolding(
                    ticker="HOLD_STOCK", quantity=10, avg_price=100.0,
                    current_price=100.0, unrealized_pnl=0.0, broker_source="alpaca",
                ),
            ]
        )
        verdicts = [
            FinalVerdict(
                ticker="HOLD_STOCK",
                final_signal="HOLD",
                overall_confidence=0.5,
                analyst_signals={"valuation_scout": "HOLD"},
                risk_summary="",
                key_drivers=[],
                session_id="s1",
            )
        ]
        insight = PortfolioInsight(
            tickers=["HOLD_STOCK"],
            verdicts=verdicts,
            portfolio_signal="HOLD",
            diversification_score=0.5,
        )
        report = syncer.get_comparison(portfolio, insight)
        assert "hold" in report.comparisons[0].action_hint.lower()

    async def test_comparison_unmapped_ticker(self):
        from integrations.portfolio_sync import PortfolioSyncer, UnifiedHolding, UnifiedPortfolio

        syncer = PortfolioSyncer(
            zerodha_client=None, alpaca_client=None, conductor=AsyncMock()
        )
        portfolio = UnifiedPortfolio(
            holdings=[
                UnifiedHolding(
                    ticker="", quantity=10, avg_price=100.0,
                    current_price=100.0, unrealized_pnl=0.0, broker_source="zerodha",
                ),
            ]
        )
        # No insight for empty ticker
        insight = _make_portfolio_insight([])
        report = syncer.get_comparison(portfolio, insight)
        assert report.comparisons[0].action_hint == "Unmapped"
        assert report.comparisons[0].equityiq_signal == ""

    async def test_comparison_analysis_unavailable(self):
        from integrations.portfolio_sync import PortfolioSyncer, UnifiedHolding, UnifiedPortfolio

        syncer = PortfolioSyncer(
            zerodha_client=None, alpaca_client=None, conductor=AsyncMock()
        )
        portfolio = UnifiedPortfolio(
            holdings=[
                UnifiedHolding(
                    ticker="MISSING", quantity=10, avg_price=100.0,
                    current_price=100.0, unrealized_pnl=0.0, broker_source="alpaca",
                ),
            ]
        )
        # Insight exists but no verdict for MISSING
        insight = _make_portfolio_insight(["OTHER"])
        report = syncer.get_comparison(portfolio, insight)
        assert report.comparisons[0].action_hint == "Analysis unavailable"


# ---------------------------------------------------------------------------
# Scheduler Tests (FR-4)
# ---------------------------------------------------------------------------

class TestScheduler:
    """FR-4: Periodic refresh scheduler."""

    async def test_scheduler_start_stop(self):
        from integrations.portfolio_sync import PortfolioSyncer

        syncer = PortfolioSyncer(
            zerodha_client=None, alpaca_client=None, conductor=AsyncMock()
        )
        assert not syncer.scheduler_running
        syncer.start_scheduler(interval_minutes=10)
        assert syncer.scheduler_running
        await syncer.stop_scheduler()
        assert not syncer.scheduler_running

    async def test_scheduler_clamp_interval(self):
        from integrations.portfolio_sync import PortfolioSyncer

        syncer = PortfolioSyncer(
            zerodha_client=None, alpaca_client=None, conductor=AsyncMock()
        )
        syncer.start_scheduler(interval_minutes=2)  # Below minimum of 5
        assert syncer._refresh_interval_minutes >= 5
        await syncer.stop_scheduler()

    async def test_scheduler_no_duplicate(self):
        from integrations.portfolio_sync import PortfolioSyncer

        syncer = PortfolioSyncer(
            zerodha_client=None, alpaca_client=None, conductor=AsyncMock()
        )
        syncer.start_scheduler(interval_minutes=10)
        task1 = syncer._scheduler_task
        syncer.start_scheduler(interval_minutes=10)  # Duplicate -- should not replace
        assert syncer._scheduler_task is task1
        await syncer.stop_scheduler()


# ---------------------------------------------------------------------------
# Full Sync Flow (FR-5)
# ---------------------------------------------------------------------------

class TestFullSync:
    """End-to-end sync flow."""

    async def test_full_sync_flow(self):
        from integrations.portfolio_sync import PortfolioSyncer

        zerodha_client = AsyncMock()
        zerodha_client.get_portfolio_summary = AsyncMock(
            return_value=_make_zerodha_portfolio()
        )
        alpaca_client = AsyncMock()
        alpaca_client.get_portfolio_summary = AsyncMock(
            return_value=_make_alpaca_portfolio()
        )

        conductor = AsyncMock()

        async def mock_analyze(tickers, session_id=None):
            return _make_portfolio_insight(tickers)

        conductor.analyze_portfolio = AsyncMock(side_effect=mock_analyze)

        syncer = PortfolioSyncer(
            zerodha_client=zerodha_client,
            alpaca_client=alpaca_client,
            conductor=conductor,
        )
        report = await syncer.sync(brokers="all")
        assert report is not None
        assert report.total_holdings == 4
        assert report.analyzed_count > 0
        assert len(report.comparisons) == 4

    async def test_sync_returns_cached_report(self):
        from integrations.portfolio_sync import PortfolioSyncer

        zerodha_client = AsyncMock()
        zerodha_client.get_portfolio_summary = AsyncMock(
            return_value=_make_zerodha_portfolio()
        )
        conductor = AsyncMock()
        conductor.analyze_portfolio = AsyncMock(
            return_value=_make_portfolio_insight(["RELIANCE.NS", "TCS.NS"])
        )

        syncer = PortfolioSyncer(
            zerodha_client=zerodha_client,
            alpaca_client=None,
            conductor=conductor,
        )
        report1 = await syncer.sync(brokers="zerodha")
        assert report1 is not None
        # Last report should be cached
        assert syncer.last_report is not None
        assert syncer.last_sync_time is not None

    async def test_sync_analysis_failure_returns_partial(self):
        from integrations.portfolio_sync import PortfolioSyncer

        alpaca_client = AsyncMock()
        alpaca_client.get_portfolio_summary = AsyncMock(
            return_value=_make_alpaca_portfolio()
        )
        conductor = AsyncMock()
        conductor.analyze_portfolio = AsyncMock(side_effect=Exception("Analysis failed"))

        syncer = PortfolioSyncer(
            zerodha_client=None,
            alpaca_client=alpaca_client,
            conductor=conductor,
        )
        report = await syncer.sync(brokers="alpaca")
        # Should still return a report with holdings but no analysis
        assert report is not None
        assert report.total_holdings == 2
        # All comparisons should show "Analysis unavailable"
        for c in report.comparisons:
            assert c.action_hint == "Analysis unavailable"
