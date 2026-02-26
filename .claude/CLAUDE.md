# EquityIQ — Claude Code Context

## Project Overview

**EquityIQ** is a multi-agent stock intelligence system.
Stack: **Google ADK** + **A2A Protocol v0.3.0** + **Gemini 3 Flash** (`gemini-3-flash-preview`).
7 specialist agents run in parallel, then a synthesizer fuses their signals → final BUY/HOLD/SELL verdict.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Agent Framework | Google Agent Development Kit (ADK) |
| Agent Protocol | A2A v0.3.0 (JSONRPC transport) |
| LLM | Gemini 3 Flash (`gemini-3-flash-preview`) |
| Backend | FastAPI + uvicorn |
| ML Synthesis | XGBoost + scikit-learn |
| Memory | SQLite (local) / Firestore (GCP) |
| Frontend | Next.js + TypeScript + Tailwind CSS |
| Deployment | Vertex AI Agent Engine + Cloud Run |
| CI/CD | Google Cloud Build |
| Async HTTP | httpx |
| Validation | Pydantic v2 |
| Caching | cachetools.TTLCache |

---

## The 7 Agents

| Agent | Port | Responsibility | Data Source |
|---|---|---|---|
| `valuation_scout.py` | 8001 | Fundamentals, valuation ratios | Polygon.io |
| `momentum_tracker.py` | 8002 | Price trends, RSI, MACD, SMAs | Polygon.io + technical_engine |
| `pulse_monitor.py` | 8003 | News sentiment, event detection | NewsAPI + Polygon |
| `economy_watcher.py` | 8004 | Macro indicators, Fed policy, GDP | FRED API |
| `compliance_checker.py` | 8005 | SEC filings, regulatory risk | SEC Edgar |
| `signal_synthesizer.py` | 8006 | Fuses all 5 signals → final verdict | XGBoost model |
| `risk_guardian.py` | 8007 | Beta, volatility, position sizing | Polygon.io |
| `market_conductor.py` | 8000 | Orchestrator — routes, aggregates | All agents |

---

## Build Order (what is done vs pending)

```
DONE:
  1. config/data_contracts.py      ← Pydantic schemas for all 9 data contracts
  2. config/analyst_personas.py    ← System prompts for all 7 agents
  3. tools/polygon_connector.py    ← Polygon.io async wrapper, TTL cache (5 min)
  4. tools/fred_connector.py       ← FRED async wrapper, TTL cache (1 hr)
  5. tools/news_connector.py       ← NewsAPI wrapper + sentiment scoring
  6. tools/sec_connector.py        ← SEC Edgar wrapper + risk scoring
  7. tools/technical_engine.py     ← Pure Python RSI, MACD, SMA, volatility

PENDING (next up, in order):
  8. models/signal_fusion.py       ← XGBoost signal synthesis
  9. models/risk_calculator.py     ← Portfolio risk math (beta, correlation)
  10. memory/insight_vault.py      ← SQLite session storage
  11. memory/history_retriever.py  ← Query past analyses
  12. agents/valuation_scout.py    ← First agent — understand the ADK pattern here
  13. agents/momentum_tracker.py
  14. agents/pulse_monitor.py
  15. agents/economy_watcher.py
  16. agents/compliance_checker.py
  17. agents/risk_guardian.py
  18. agents/signal_synthesizer.py
  19. agents/market_conductor.py   ← Orchestrator
  20. app.py                       ← FastAPI entry point
  21. scripts/                     ← Shell scripts (launch, stop, health check)
  22. evaluation/                  ← Quality assessor, benchmark cases, backtester
  23. frontend/                    ← Next.js dashboard
```

---

## Key File Paths

```
equityiq/
├── config/
│   ├── data_contracts.py     ← Pydantic schemas (AnalystReport, FinalVerdict, etc.)
│   └── analyst_personas.py   ← System prompt strings + PERSONAS dict
├── tools/
│   ├── polygon_connector.py  ← get_fundamentals(), get_price_history(), get_company_news()
│   ├── fred_connector.py     ← get_macro_indicators()
│   ├── news_connector.py     ← get_news_sentiment()
│   ├── sec_connector.py      ← get_sec_filings(), score_risk()
│   └── technical_engine.py   ← calc_rsi(), calc_macd(), calc_sma(), calc_volatility()
├── models/                   ← PENDING
├── memory/                   ← PENDING
├── agents/                   ← PENDING
├── evaluation/               ← PENDING
├── scripts/                  ← PENDING
├── frontend/                 ← PENDING
├── deploy/                   ← GCP configs
├── docs/
│   └── 01_project_overview.md
├── requirements.txt
├── .env.example              ← Copy to .env, fill in API keys
└── app.py                    ← PENDING
```

---

## Data Schemas (config/data_contracts.py)

All agents return a subclass of `AnalystReport`. The synthesizer returns `FinalVerdict`.

```
AnalystReport (base)
├── ValuationReport    → pe_ratio, pb_ratio, revenue_growth, debt_to_equity, fcf_yield, intrinsic_value_gap
├── MomentumReport     → rsi_14, macd_signal, above_sma_50, above_sma_200, volume_trend, price_momentum_score
├── PulseReport        → sentiment_score, article_count, top_headlines, event_flags
├── EconomyReport      → gdp_growth, inflation_rate, fed_funds_rate, unemployment_rate, macro_regime
├── ComplianceReport   → latest_filing_type, days_since_filing, risk_flags, risk_score
└── RiskGuardianReport → beta, annualized_volatility, sharpe_ratio, max_drawdown, suggested_position_size, var_95

FinalVerdict           → ticker, final_signal (5-level), overall_confidence, price_target, analyst_signals, risk_summary, key_drivers, session_id
PortfolioInsight       → tickers, verdicts, portfolio_signal, diversification_score, top_pick
```

---

## API Endpoints (app.py — pending)

| Method | Endpoint | Description |
|---|---|---|
| POST | `/analyze/{ticker}` | Single stock analysis |
| POST | `/portfolio` | Multi-stock portfolio analysis |
| POST | `/chat` | Natural language interface |
| GET | `/history/{ticker}` | Past analyses for a ticker |
| GET | `/history/{ticker}/trend` | Signal trend over time |
| GET | `/health` | Status of all 7 agents |

---

## Environment Variables (.env)

```
GOOGLE_API_KEY       ← Gemini (required for all agents)
POLYGON_API_KEY      ← Stock data, news, fundamentals
FRED_API_KEY         ← Macro economic data
NEWS_API_KEY         ← NewsAPI headlines
ENVIRONMENT          ← local | production
SQLITE_DB_PATH       ← ./data/equityiq.db
GCP_PROJECT_ID       ← For deployment only
GCP_REGION           ← us-central1
LOG_LEVEL            ← DEBUG | INFO | WARNING | ERROR
```

Agent URLs in .env when ENVIRONMENT=local:
`VALUATION_AGENT_URL=http://localhost:8001` … through `RISK_AGENT_URL=http://localhost:8007`

---

## Code Conventions

- All tool functions are **async** (`async def`, `await httpx.AsyncClient`)
- **TTL caching**: `cachetools.TTLCache` wraps every API call — 5 min for Polygon, 1 hr for FRED
- **Pydantic v2**: `BaseModel`, `Field(...)`, `@field_validator`, `ConfigDict`
- `Field(...)` = required, `Field(default=None)` = optional, `Field(default_factory=...)` = auto-generated
- All agent outputs clamp numeric fields (confidence to [0,1], momentum to [-1,1], etc.)
- Error handling: `try/except` wraps all external calls — never let a failed API crash an agent
- Import order: stdlib → third-party → local (`config/`, `tools/`, `models/`, `memory/`)
- Signals are always `Literal["BUY", "HOLD", "SELL"]` from agents, `Literal["STRONG_BUY","BUY","HOLD","SELL","STRONG_SELL"]` from synthesizer

---

## Running Locally

```bash
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in your API keys

bash scripts/launch_agents.sh    # starts all 7 agents (ports 8001-8007)
python app.py                    # starts FastAPI on port 8000

# test
curl -X POST http://localhost:8000/analyze/AAPL
curl -X POST http://localhost:8000/health
```

---

## Key Design Decisions

1. **Parallel execution** — all 7 agents run via `asyncio.gather()`, not sequentially
2. **XGBoost synthesis** — trained ML model (not weighted average) fuses the 5 analyst signals
3. **ComplianceChecker hard override** — `going_concern` or `restatement` flag always forces SELL regardless of other signals
4. **RiskGuardian is separate** — it informs position sizing, not the directional signal (different weight)
5. **TTL caching** — critical for staying within Polygon free tier (5 req/min)
6. **SQLite local → Firestore GCP** — `ENVIRONMENT` var controls which storage backend is used
7. **Graceful degradation** — missing agent reports reduce `overall_confidence` by 0.20; system still produces output

---

## Signal Weighting (SignalSynthesizer)

Default weights:
- ValuationScout: 0.25
- MomentumTracker: 0.20
- PulseMonitor: 0.20
- EconomyWatcher: 0.20
- ComplianceChecker: 0.15

Adjustments:
- Contraction/stagflation regime → EconomyWatcher weight → 0.30
- Earnings season → PulseMonitor weight → 0.30
