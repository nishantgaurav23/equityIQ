# Architecture

EquityIQ is a multi-agent stock intelligence system. Seven specialist AI agents analyze stocks in parallel, and a SignalSynthesizer fuses their signals into a final verdict using XGBoost.

## System Overview

```
Request (ticker)
    │
    ▼
┌─────────────────────────────────────┐
│       MarketConductor (8000)        │
│         Orchestrator Layer          │
│    asyncio.gather() all agents      │
├──────┬──────┬──────┬──────┬────────┤
│ VS   │ MT   │ PM   │ EW   │  CC    │
│ 8001 │ 8002 │ 8003 │ 8004 │ 8005   │
├──────┴──────┴──────┴──────┴────────┤
│      SignalSynthesizer (8006)       │
│   XGBoost fusion → FinalVerdict     │
├────────────────────────────────────┤
│       RiskGuardian (8007)           │
│   Beta, volatility, sizing          │
└────────────────────────────────────┘
    │
    ▼
FinalVerdict (5-level signal)
```

## Agent Table

| Agent | Port | Responsibility | Data Source | Output |
|-------|------|---------------|------------|--------|
| **ValuationScout** | 8001 | Fundamentals: PE, PB, FCF yield, intrinsic value gap | Polygon.io | ValuationReport |
| **MomentumTracker** | 8002 | Technicals: RSI, MACD, SMAs, volume trends | Polygon.io + technical_engine | MomentumReport |
| **PulseMonitor** | 8003 | Sentiment: news analysis, event detection | NewsAPI + Polygon | PulseReport |
| **EconomyWatcher** | 8004 | Macro: GDP, inflation, Fed rate, unemployment | FRED API | EconomyReport |
| **ComplianceChecker** | 8005 | Regulatory: SEC filings, risk flags | SEC Edgar | ComplianceReport |
| **SignalSynthesizer** | 8006 | Fusion: combines 5 agent signals → final verdict | All agent reports | FinalVerdict |
| **RiskGuardian** | 8007 | Risk: beta, volatility, Sharpe, position sizing | Polygon.io | RiskGuardianReport |
| **MarketConductor** | 8000 | Orchestration: routes requests, aggregates results | All agents | FinalVerdict / PortfolioInsight |

## Signal Flow

1. **Request**: User submits a ticker via `POST /api/v1/analyze/{ticker}`
2. **Orchestration**: MarketConductor dispatches to all 6 analysis agents in parallel via `asyncio.gather()`
3. **Analysis**: Each agent fetches data, processes it with its LLM (Gemini 3 Flash), and returns a typed AnalystReport
4. **Synthesis**: SignalSynthesizer receives all 5 directional reports and fuses them using XGBoost (fallback: weighted average)
5. **Risk Assessment**: RiskGuardian independently calculates beta, volatility, and position sizing
6. **Compliance Override**: If ComplianceChecker detects `going_concern` or `restatement`, the verdict is forced to SELL
7. **Storage**: Final verdict is persisted to InsightVault (SQLite local / Firestore production)
8. **Response**: FinalVerdict returned to client with 5-level signal

## Signal Weighting

The SignalSynthesizer uses these default weights for weighted-average fallback:

| Agent | Default Weight | Notes |
|-------|---------------|-------|
| ValuationScout | 0.25 | Highest weight -- fundamentals anchor |
| MomentumTracker | 0.20 | |
| PulseMonitor | 0.20 | Boosted to 0.30 during earnings season |
| EconomyWatcher | 0.20 | Boosted to 0.30 during contraction/stagflation |
| ComplianceChecker | 0.15 | Hard override bypasses weights |

## 5-Level Verdict Scale

| Signal | Confidence Requirement |
|--------|----------------------|
| STRONG_BUY | overall_confidence >= 0.75 |
| BUY | Majority BUY signals |
| HOLD | Mixed or insufficient signals |
| SELL | Majority SELL signals |
| STRONG_SELL | overall_confidence >= 0.75 |

## Key Design Decisions

### 1. Parallel Execution
All agents run via `asyncio.gather()`, not sequentially. This keeps total latency close to the slowest single agent rather than the sum of all agents.

### 2. XGBoost Synthesis
A trained XGBoost model fuses agent signals into a final verdict. If the model is unavailable, a weighted average fallback is used. This gives the system a data-driven edge while maintaining reliability.

### 3. Compliance Hard Override
ComplianceChecker `going_concern` or `restatement` flags always force a SELL verdict regardless of other signals. Regulatory risk is non-negotiable.

### 4. Graceful Degradation
If any agent fails (timeout, API error), the system continues with remaining agents. Missing agents reduce overall confidence by 0.20 and a warning is added to key_drivers.

### 5. RiskGuardian Separation
RiskGuardian informs position sizing but does not contribute to the directional signal. Position size is capped at 10% max per stock.

### 6. TTL Caching
All external API calls use TTLCache (Polygon: 5min, FRED: 1hr). Critical for staying within Polygon free tier rate limits (5 req/min).

### 7. Monolith-in-Container
All agents run as async functions within a single FastAPI process, deployed in one Cloud Run container. This keeps costs under $50/month while maintaining the multi-agent architecture internally.

### 8. SQLite Local, Firestore Production
The `ENVIRONMENT` variable controls which storage backend is used. Local dev uses SQLite via aiosqlite; production uses Google Firestore.

## Data Schemas

All data flows through Pydantic v2 models defined in `config/data_contracts.py`:

```
AnalystReport (base)
├── ValuationReport    → pe_ratio, pb_ratio, revenue_growth, debt_to_equity, fcf_yield
├── MomentumReport     → rsi_14, macd_signal, above_sma_50, above_sma_200, volume_trend
├── PulseReport        → sentiment_score, article_count, top_headlines, event_flags
├── EconomyReport      → gdp_growth, inflation_rate, fed_funds_rate, unemployment_rate
├── ComplianceReport   → latest_filing_type, days_since_filing, risk_flags, risk_score
└── RiskGuardianReport → beta, annualized_volatility, sharpe_ratio, max_drawdown, var_95

FinalVerdict → ticker, final_signal, overall_confidence, analyst_signals, risk_summary
PortfolioInsight → tickers, verdicts, portfolio_signal, diversification_score, top_pick
```

## Tech Stack

| Layer | Technology |
|-------|------------|
| Agent Framework | Google ADK + A2A v0.3.0 (JSONRPC) |
| LLM | Gemini 3 Flash (`gemini-3-flash-preview`) |
| Backend | Python 3.12 / FastAPI + uvicorn |
| ML Synthesis | XGBoost + scikit-learn |
| Validation | Pydantic v2 + pydantic-settings |
| Caching | cachetools.TTLCache |
| Memory | SQLite (local) / Firestore (production) |
| Frontend | Next.js + TypeScript + Tailwind |
| Deployment | GCP Cloud Run (single container) |
