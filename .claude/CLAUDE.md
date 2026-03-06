# EquityIQ -- Claude Code Context

## Project
Multi-agent stock intelligence system. 7 specialist AI agents analyze stocks in parallel, XGBoost synthesizer fuses signals into BUY/HOLD/SELL verdict.
Stack: Google ADK + A2A Protocol v0.3.0 + Gemini 3 Flash. Deployment: GCP Cloud Run (single container, under $50/month).

## Key Rules
- NEVER hardcode API keys. All secrets via .env -> config/settings.py.
- NEVER let a failed API call crash an agent. Always try/except on external calls.
- NEVER assign confidence > 0.70 on fewer than 3 news articles.
- ComplianceChecker going_concern or restatement -> always SELL override.
- STRONG_BUY/STRONG_SELL requires overall_confidence >= 0.75.
- RiskGuardian: suggested_position_size never > 0.10 (10% max per stock).
- Git author: nishantgaurav23 / nishantgaurav23@gmail.com

## Tech Stack
| Layer | Technology |
|-------|------------|
| Agent Framework | Google ADK + A2A v0.3.0 (JSONRPC) |
| LLM | Gemini 3 Flash (`gemini-3-flash-preview`) |
| Backend | Python 3.12 / FastAPI + uvicorn |
| ML Synthesis | XGBoost + scikit-learn |
| Validation | Pydantic v2 + pydantic-settings |
| Async HTTP | httpx + aiohttp |
| Caching | cachetools.TTLCache (Polygon 5min, FRED 1hr) |
| Memory (local) | SQLite via aiosqlite |
| Memory (prod) | Firestore |
| Frontend | Next.js + TypeScript + Tailwind |
| Deployment | Cloud Run (single container, 0-4 instances) |
| CI/CD | GitHub Actions |
| Secrets | GCP Secret Manager |
| Testing | pytest + pytest-asyncio |
| Linting | ruff (line-length: 100) |

## The 7 Agents

| Agent | Port | Responsibility | Data Source |
|-------|------|---------------|------------|
| `valuation_scout.py` | 8001 | Fundamentals, valuation ratios | Polygon.io |
| `momentum_tracker.py` | 8002 | Price trends, RSI, MACD, SMAs | Polygon.io + technical_engine |
| `pulse_monitor.py` | 8003 | News sentiment, event detection | NewsAPI + Polygon |
| `economy_watcher.py` | 8004 | Macro indicators, Fed policy, GDP | FRED API |
| `compliance_checker.py` | 8005 | SEC filings, regulatory risk | SEC Edgar |
| `signal_synthesizer.py` | 8006 | Fuses all 5 signals -> final verdict | XGBoost model |
| `risk_guardian.py` | 8007 | Beta, volatility, position sizing | Polygon.io |
| `market_conductor.py` | 8000 | Orchestrator -- routes, aggregates | All agents |

## Project Structure
```
equityiq/
├── .claude/commands/        <- Spec-driven development commands
├── specs/                   <- Spec folders (spec.md + checklist.md each)
├── config/
│   ├── data_contracts.py    <- Pydantic schemas (AnalystReport, FinalVerdict, etc.)
│   ├── analyst_personas.py  <- System prompts + PERSONAS dict
│   ├── settings.py          <- pydantic-settings config (PENDING)
│   └── logging.py           <- Structured logging (PENDING)
├── tools/
│   ├── polygon_connector.py <- get_fundamentals(), get_price_history(), get_company_news()
│   ├── fred_connector.py    <- get_macro_indicators()
│   ├── news_connector.py    <- get_news_sentiment()
│   ├── sec_connector.py     <- get_sec_filings(), score_risk()
│   └── technical_engine.py  <- calc_rsi(), calc_macd(), calc_sma(), calc_volatility()
├── models/                  <- XGBoost signal fusion, risk calculator (PENDING)
├── memory/                  <- SQLite/Firestore persistence (PENDING)
├── agents/                  <- ADK agents (PENDING)
├── tests/                   <- Test suite (mirror app structure)
├── evaluation/              <- Quality, benchmarks, backtesting (PENDING)
├── scripts/                 <- Launch, stop, health check (PENDING)
├── frontend/                <- Next.js dashboard (PENDING)
├── deploy/                  <- GCP Cloud Run configs (PENDING)
├── .github/workflows/       <- CI/CD pipelines (PENDING)
├── roadmap.md               <- Full spec index + phase tables
├── design.md                <- Architecture + deployment design
├── pyproject.toml           <- Single source of truth for deps (PENDING)
├── Makefile                 <- Developer commands (PENDING)
├── Dockerfile               <- Multi-stage build (PENDING)
└── app.py                   <- FastAPI entry point (PENDING)
```

## Spec Folder Convention
Each spec has a dedicated folder under `specs/`:
```
specs/spec-{number}-{short-name}/
  spec.md        <- detailed specification
  checklist.md   <- implementation progress tracker
```
Full spec index is in `roadmap.md`.

## Spec-Driven Development Commands

| Command | Invocation | Purpose |
|---------|------------|---------|
| **Start spec dev** | `/start-spec-dev S1.1 dependency-declaration` | Full lifecycle: create, check deps, implement, verify (auto or step-by-step) |
| **Create spec** | `/create-spec S1.1 dependency-declaration` | Creates spec.md + checklist.md in spec folder from roadmap |
| **Check deps** | `/check-spec-deps S4.1` | Verifies all prerequisite specs are implemented and tests pass |
| **Implement spec** | `/implement-spec S1.1` | TDD implementation following spec + checklist |
| **Verify spec** | `/verify-spec S1.1` | Post-implementation audit: tests, lint, outcomes, wiring |

## Commands
```bash
# Local (after Phase 1 is done)
make venv            # Create .venv at root
make install         # Install runtime deps
make install-dev     # Install + pytest/ruff
make local-dev       # uvicorn with hot reload
make local-test      # pytest
make local-lint      # ruff check + format

# Docker (after Phase 11 is done)
make dev             # docker-compose up --build
make test            # pytest in container
```

## Environment
- **venv**: `venv` at project root (Python 3.12)
- **Package manager**: `uv` or `pip` -- single source of truth: `pyproject.toml`
- **Docker build context**: repo root

## Testing
- Run from project root: `source venv/bin/activate && python -m pytest tests/ -v --tb=short`
- All external services mocked (Polygon, FRED, NewsAPI, SEC Edgar, Gemini)
- pytest-asyncio for async test support
- A file is NEVER considered done until its tests pass

## Code Standards
- Async everywhere (async def, await, httpx.AsyncClient, aiosqlite)
- Pydantic v2 models for all data in/out
- TTL caching on all external API calls (never skip this)
- field_validator for clamping (confidence [0,1], momentum [-1,1], etc.)
- try/except wraps all external calls -- never crash an agent
- Import order: stdlib -> third-party -> local (config/, tools/, models/, memory/)
- Signals: BUY/HOLD/SELL from agents, STRONG_BUY/BUY/HOLD/SELL/STRONG_SELL from synthesizer
- Ruff for linting and formatting (line length: 100)

## Data Schemas (config/data_contracts.py)

```
AnalystReport (base)
├── ValuationReport    -> pe_ratio, pb_ratio, revenue_growth, debt_to_equity, fcf_yield, intrinsic_value_gap
├── MomentumReport     -> rsi_14, macd_signal, above_sma_50, above_sma_200, volume_trend, price_momentum_score
├── PulseReport        -> sentiment_score, article_count, top_headlines, event_flags
├── EconomyReport      -> gdp_growth, inflation_rate, fed_funds_rate, unemployment_rate, macro_regime
├── ComplianceReport   -> latest_filing_type, days_since_filing, risk_flags, risk_score
└── RiskGuardianReport -> beta, annualized_volatility, sharpe_ratio, max_drawdown, suggested_position_size, var_95

FinalVerdict           -> ticker, final_signal (5-level), overall_confidence, price_target, analyst_signals, risk_summary, key_drivers, session_id
PortfolioInsight       -> tickers, verdicts, portfolio_signal, diversification_score, top_pick
```

## Signal Weighting (SignalSynthesizer)

Default weights:
- ValuationScout: 0.25, MomentumTracker: 0.20, PulseMonitor: 0.20, EconomyWatcher: 0.20, ComplianceChecker: 0.15

Adjustments:
- Contraction/stagflation regime -> EconomyWatcher weight -> 0.30
- Earnings season -> PulseMonitor weight -> 0.30

## Key Design Decisions

1. **Parallel execution** -- all agents run via `asyncio.gather()`, not sequentially
2. **XGBoost synthesis** -- trained ML model fuses signals (fallback: weighted average)
3. **ComplianceChecker hard override** -- going_concern/restatement always forces SELL
4. **RiskGuardian is separate** -- informs position sizing, not directional signal
5. **TTL caching** -- critical for Polygon free tier (5 req/min)
6. **SQLite local -> Firestore GCP** -- ENVIRONMENT var controls backend
7. **Graceful degradation** -- missing agent reduces confidence by 0.20
8. **Monolith-in-container** -- all agents in single Cloud Run container for cost (<$50/month)
