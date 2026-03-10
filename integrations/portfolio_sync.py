"""Portfolio sync -- import holdings from brokers, analyze, and compare."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

MIN_REFRESH_INTERVAL = 5  # minutes
MAX_BATCH_SIZE = 10


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


class UnifiedHolding(BaseModel):
    """A single holding from any broker, normalized to common format."""

    ticker: str  # EquityIQ ticker format
    quantity: float
    avg_price: float
    current_price: float
    unrealized_pnl: float
    broker_source: str  # "zerodha" or "alpaca"


class UnifiedPortfolio(BaseModel):
    """Merged portfolio from one or more brokers."""

    holdings: list[UnifiedHolding] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class HoldingComparison(BaseModel):
    """Side-by-side: current holding vs EquityIQ recommendation."""

    ticker: str
    broker_source: str
    quantity: float
    avg_price: float
    current_price: float
    unrealized_pnl: float
    equityiq_signal: str = ""
    equityiq_confidence: float = 0.0
    action_hint: str = ""


class SyncReport(BaseModel):
    """Full sync report: comparisons + metadata."""

    comparisons: list[HoldingComparison] = Field(default_factory=list)
    total_holdings: int = 0
    analyzed_count: int = 0
    sync_errors: list[str] = Field(default_factory=list)
    synced_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Action Hint Logic
# ---------------------------------------------------------------------------


def _compute_action_hint(signal: str) -> str:
    """Determine action hint based on EquityIQ signal for a held stock."""
    signal_upper = signal.upper()
    if signal_upper in ("STRONG_BUY", "BUY"):
        return "Consider adding"
    if signal_upper in ("STRONG_SELL", "SELL"):
        return "Consider selling"
    if signal_upper == "HOLD":
        return "Hold -- aligns with position"
    return "Review needed"


# ---------------------------------------------------------------------------
# PortfolioSyncer
# ---------------------------------------------------------------------------


class PortfolioSyncer:
    """Imports broker holdings, runs EquityIQ analysis, and compares."""

    def __init__(
        self,
        zerodha_client=None,
        alpaca_client=None,
        conductor=None,
    ):
        self._zerodha = zerodha_client
        self._alpaca = alpaca_client
        self._conductor = conductor
        self._scheduler_task: asyncio.Task | None = None
        self._refresh_interval_minutes: int = 60
        self.last_report: SyncReport | None = None
        self.last_sync_time: datetime | None = None

    # -- Properties --

    @property
    def scheduler_running(self) -> bool:
        return self._scheduler_task is not None and not self._scheduler_task.done()

    # -- FR-1: Import Holdings --

    async def import_holdings(self, brokers: str = "all") -> UnifiedPortfolio:
        """Fetch holdings from one or both brokers and merge."""
        holdings: list[UnifiedHolding] = []
        errors: list[str] = []

        fetch_zerodha = brokers in ("all", "zerodha")
        fetch_alpaca = brokers in ("all", "alpaca")

        if fetch_zerodha and self._zerodha is not None:
            try:
                zp = await self._zerodha.get_portfolio_summary()
                for h in zp.holdings:
                    holdings.append(
                        UnifiedHolding(
                            ticker=h.equityiq_ticker,
                            quantity=float(h.quantity),
                            avg_price=h.average_price,
                            current_price=h.last_price,
                            unrealized_pnl=h.pnl,
                            broker_source="zerodha",
                        )
                    )
            except Exception as e:
                logger.error("Zerodha import failed: %s", e)
                errors.append(f"Zerodha import failed: {e}")

        if fetch_alpaca and self._alpaca is not None:
            try:
                ap = await self._alpaca.get_portfolio_summary()
                for p in ap.positions:
                    holdings.append(
                        UnifiedHolding(
                            ticker=p.equityiq_ticker,
                            quantity=p.qty,
                            avg_price=p.avg_entry_price,
                            current_price=p.current_price,
                            unrealized_pnl=p.unrealized_pl,
                            broker_source="alpaca",
                        )
                    )
            except Exception as e:
                logger.error("Alpaca import failed: %s", e)
                errors.append(f"Alpaca import failed: {e}")

        return UnifiedPortfolio(holdings=holdings, errors=errors)

    # -- FR-2: Run Analysis --

    async def run_analysis(self, portfolio: UnifiedPortfolio):
        """Run EquityIQ analysis on unique tickers from the portfolio.

        Returns PortfolioInsight or None if portfolio is empty.
        Batches in groups of MAX_BATCH_SIZE.
        """
        # Deduplicate and filter empty tickers
        unique_tickers = sorted({h.ticker for h in portfolio.holdings if h.ticker})
        if not unique_tickers:
            return None

        # Batch if > MAX_BATCH_SIZE
        if len(unique_tickers) <= MAX_BATCH_SIZE:
            return await self._conductor.analyze_portfolio(unique_tickers)

        # Multiple batches
        from config.data_contracts import PortfolioInsight

        all_verdicts = []
        all_tickers = []
        for i in range(0, len(unique_tickers), MAX_BATCH_SIZE):
            batch = unique_tickers[i : i + MAX_BATCH_SIZE]
            insight = await self._conductor.analyze_portfolio(batch)
            if insight:
                all_verdicts.extend(insight.verdicts)
                all_tickers.extend(insight.tickers)

        if not all_verdicts:
            return None

        return PortfolioInsight(
            tickers=all_tickers,
            verdicts=all_verdicts,
            portfolio_signal="HOLD",
            diversification_score=0.5,
            top_pick=all_tickers[0] if all_tickers else None,
        )

    # -- FR-3: Side-by-Side Comparison --

    def get_comparison(self, portfolio: UnifiedPortfolio, insight) -> SyncReport:
        """Generate a SyncReport pairing holdings with EquityIQ verdicts."""
        # Build verdict lookup
        verdict_map: dict[str, object] = {}
        if insight and hasattr(insight, "verdicts"):
            for v in insight.verdicts:
                verdict_map[v.ticker] = v

        comparisons = []
        analyzed_count = 0

        for h in portfolio.holdings:
            if not h.ticker:
                comparisons.append(
                    HoldingComparison(
                        ticker=h.ticker,
                        broker_source=h.broker_source,
                        quantity=h.quantity,
                        avg_price=h.avg_price,
                        current_price=h.current_price,
                        unrealized_pnl=h.unrealized_pnl,
                        equityiq_signal="",
                        equityiq_confidence=0.0,
                        action_hint="Unmapped",
                    )
                )
                continue

            verdict = verdict_map.get(h.ticker)
            if verdict is None:
                comparisons.append(
                    HoldingComparison(
                        ticker=h.ticker,
                        broker_source=h.broker_source,
                        quantity=h.quantity,
                        avg_price=h.avg_price,
                        current_price=h.current_price,
                        unrealized_pnl=h.unrealized_pnl,
                        equityiq_signal="",
                        equityiq_confidence=0.0,
                        action_hint="Analysis unavailable",
                    )
                )
                continue

            analyzed_count += 1
            comparisons.append(
                HoldingComparison(
                    ticker=h.ticker,
                    broker_source=h.broker_source,
                    quantity=h.quantity,
                    avg_price=h.avg_price,
                    current_price=h.current_price,
                    unrealized_pnl=h.unrealized_pnl,
                    equityiq_signal=verdict.final_signal,
                    equityiq_confidence=verdict.overall_confidence,
                    action_hint=_compute_action_hint(verdict.final_signal),
                )
            )

        return SyncReport(
            comparisons=comparisons,
            total_holdings=len(portfolio.holdings),
            analyzed_count=analyzed_count,
            sync_errors=portfolio.errors,
        )

    # -- FR-1+2+3 Combined --

    async def sync(self, brokers: str = "all") -> SyncReport:
        """Full sync: import -> analyze -> compare. Returns SyncReport."""
        portfolio = await self.import_holdings(brokers=brokers)

        try:
            insight = await self.run_analysis(portfolio)
        except Exception as e:
            logger.error("Analysis failed during sync: %s", e)
            insight = None

        report = self.get_comparison(portfolio, insight)
        self.last_report = report
        self.last_sync_time = datetime.now(timezone.utc)
        return report

    # -- FR-4: Scheduler --

    def start_scheduler(self, interval_minutes: int = 60) -> None:
        """Start periodic background sync. Clamps interval to >= 5 min."""
        if self.scheduler_running:
            logger.info("Scheduler already running, skipping duplicate start")
            return

        self._refresh_interval_minutes = max(interval_minutes, MIN_REFRESH_INTERVAL)
        self._scheduler_task = asyncio.get_event_loop().create_task(self._scheduler_loop())
        logger.info(
            "Portfolio sync scheduler started (interval=%d min)",
            self._refresh_interval_minutes,
        )

    async def stop_scheduler(self) -> None:
        """Stop the background scheduler."""
        if self._scheduler_task and not self._scheduler_task.done():
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        self._scheduler_task = None
        logger.info("Portfolio sync scheduler stopped")

    async def _scheduler_loop(self) -> None:
        """Background loop that runs sync() at the configured interval."""
        while True:
            try:
                await self.sync()
                logger.info("Scheduled portfolio sync completed")
            except Exception as e:
                logger.error("Scheduled sync failed: %s", e)
            await asyncio.sleep(self._refresh_interval_minutes * 60)
