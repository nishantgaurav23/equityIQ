# Roadmap -- EquityIQ: Multi-Agent Stock Intelligence System

**Prototype target**: End-to-end stock analysis via API -- 7 agents in parallel, XGBoost synthesis, final verdict.
**Budget**: $0-50 GCP (free tier + minimal paid).
**LLM**: Gemini 3 Flash (`gemini-3-flash-preview`) for all agents.
**Out of scope for prototype**: Real-time streaming, mobile app, social trading features.
**Multi-market**: US (Polygon/SEC/FRED) + India (Yahoo/SEBI/RBI/NSE) fully supported.

---

## Tech Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Agent Framework | Google ADK + A2A v0.3.0 | Official Google agent kit, JSONRPC transport |
| LLM | Gemini 3 Flash (`gemini-3-flash-preview`) | Fast, cost-effective for parallel agent calls |
| Backend | Python 3.12 / FastAPI / uvicorn | Async, strong ecosystem, fast iteration |
| ML Synthesis | XGBoost + scikit-learn | Signal fusion beyond simple weighted average |
| Validation | Pydantic v2 + pydantic-settings | Typed schemas, env-based config |
| Async HTTP | httpx + aiohttp | Non-blocking external API calls |
| Caching | cachetools.TTLCache | Polygon 5-min, FRED 1-hr TTL |
| Memory (local) | SQLite via aiosqlite | Zero-config local persistence |
| Memory (prod) | Firestore | Managed NoSQL, generous free tier |
| Frontend | Next.js + TypeScript + Tailwind | Modern dashboard |
| Deployment | Cloud Run (single container) | Auto-scale 0-4, pay-per-use |
| CI/CD | GitHub Actions | Free 2000 min/month |
| Secrets | GCP Secret Manager | Free tier (6 active versions) |
| Testing | pytest + pytest-asyncio | Async test suite, all externals mocked |
| Linting | ruff (line-length: 100) | Fast, opinionated |

---

## GCP Budget

| Resource | Tier | Est. Monthly Cost |
|----------|------|-------------------|
| Cloud Run (1 container, 0-4 instances) | Free: 2M req, 360K GB-s | $0-5 |
| Artifact Registry | 500MB free | $0 |
| Firestore | Free: 1GB, 50K reads/day | $0 |
| Secret Manager | 6 active versions free | $0 |
| Cloud Logging | 50GB/month free | $0 |
| Gemini API | ~$0.01/analysis | $5-15 |
| Polygon.io | Free tier (5 req/min) | $0 |
| FRED / NewsAPI / SEC Edgar | Free | $0 |
| **Total (prototype)** | | **$5-20/month** |

---

## Spec Folder Convention

Each spec has a dedicated folder under `specs/`:

```
specs/
  spec-S1.1-dependency-declaration/
    spec.md        <- detailed specification
    checklist.md   <- implementation checklist / progress tracker
  spec-S1.2-developer-commands/
    spec.md
    checklist.md
  ...
```

---

## Phases Overview

| Phase | Name | Specs | Key Output |
|-------|------|-------|------------|
| 1 | Project Foundation | 5 | Runnable skeleton, config, security |
| 2 | Data Contracts & Personas | 3 | Pydantic schemas + agent system prompts |
| 3 | Data Connectors | 5 | All external API wrappers with TTL cache |
| 4 | ML Models | 3 | XGBoost signal fusion + risk calculator |
| 5 | Memory Layer | 3 | SQLite persistence + history retrieval |
| 6 | Agent Framework | 2 | ADK agent base pattern + A2A server |
| 7 | Specialist Agents | 6 | All 6 analyst/risk agents |
| 8 | Orchestration | 3 | Signal synthesizer + market conductor |
| 9 | API Layer | 4 | FastAPI endpoints, health, error handling |
| 10 | Pipeline Integration | 3 | End-to-end wired analysis pipeline |
| 11 | Infrastructure | 5 | Docker, compose, scripts, .dockerignore |
| 12 | GCP Deployment | 5 | Cloud Run, GitHub Actions, secrets |
| 13 | Frontend | 4 | Next.js dashboard |
| 14 | Evaluation & QA | 5 | Backtester, benchmarks, E2E tests |
| 16 | Intelligence Layer | 3 | Vertex AI memory, NL chat, prediction tracker |
| 17 | Integrations | 4 | Broker connectivity, portfolio sync, alerts |

---

## Phase 1 -- Project Foundation

Bootstraps the project: dependency declaration, environment config, app factory, Makefile, testing/linting setup.
Output: `make local-dev` starts a healthy FastAPI server with `/health` endpoint.

| Spec | Spec Location | Depends On | Location | Feature | Notes | Status |
|------|--------------|-----------|----------|---------|-------|--------|
| S1.1 | `specs/spec-S1.1-dependency-declaration/` | -- | `pyproject.toml`, `.env.example` | Dependency declaration | Runtime: google-adk, google-generativeai, fastapi, uvicorn, pydantic, pydantic-settings, httpx, aiohttp, cachetools, aiosqlite, xgboost, scikit-learn, pandas, numpy, python-dotenv, beautifulsoup4, lxml, colorlog. Dev: pytest, pytest-asyncio, ruff, pytest-mock, httpx | done |
| S1.2 | `specs/spec-S1.2-developer-commands/` | -- | `Makefile` | Developer commands | Targets: venv, install, install-dev, local-dev, local-test, local-lint, dev (Docker), test (Docker) | done |
| S1.3 | `specs/spec-S1.3-pydantic-settings/` | S1.1 | `config/settings.py` | Settings via pydantic-settings | Fields: GOOGLE_API_KEY, POLYGON_API_KEY, FRED_API_KEY, NEWS_API_KEY, ENVIRONMENT, SQLITE_DB_PATH, GCP_PROJECT_ID, GCP_REGION, LOG_LEVEL. All from .env | done |
| S1.4 | `specs/spec-S1.4-fastapi-skeleton/` | S1.3 | `app.py` | FastAPI app factory | Lifespan: connect DB on startup, disconnect on shutdown. GET /health returning `{"status": "ok", "agents": {...}}`. Include routers | done |
| S1.5 | `specs/spec-S1.5-logging-setup/` | S1.3 | `config/logging.py` | Structured logging | Colorlog for local, structured JSON for production. LOG_LEVEL from settings. request_id context for tracing | done |

---

## Phase 2 -- Data Contracts & Personas

All Pydantic schemas for agent I/O and system prompts for each agent's LLM persona. Already implemented -- bring under spec governance.

| Spec | Spec Location | Depends On | Location | Feature | Notes | Status |
|------|--------------|-----------|----------|---------|-------|--------|
| S2.1 | `specs/spec-S2.1-analyst-report-schemas/` | S1.1 | `config/data_contracts.py` | Base AnalystReport + 6 subclass schemas | AnalystReport, ValuationReport, MomentumReport, PulseReport, EconomyReport, ComplianceReport, RiskGuardianReport. All field_validators for clamping | done |
| S2.2 | `specs/spec-S2.2-verdict-schemas/` | S2.1 | `config/data_contracts.py` | FinalVerdict + PortfolioInsight | FinalVerdict (5-level signal, analyst_signals, risk_summary, key_drivers). PortfolioInsight (multi-stock) | done |
| S2.3 | `specs/spec-S2.3-agent-personas/` | -- | `config/analyst_personas.py` | System prompts for all 7 agents | PERSONAS dict mapping agent_name -> system prompt string. Each prompt defines domain expertise, output format, constraints | done |

---

## Phase 3 -- Data Connectors

Async API wrappers for all external data sources. TTL caching on every call. Prior implementations were removed in clean-slate commit -- must be rebuilt under spec governance with TDD.

| Spec | Spec Location | Depends On | Location | Feature | Notes | Status |
|------|--------------|-----------|----------|---------|-------|--------|
| S3.1 | `specs/spec-S3.1-polygon-connector/` | S1.3 | `tools/polygon_connector.py` | Polygon.io async wrapper | get_fundamentals(), get_price_history(), get_company_news(). TTLCache 5min. httpx.AsyncClient | done |
| S3.2 | `specs/spec-S3.2-fred-connector/` | S1.3 | `tools/fred_connector.py` | FRED API async wrapper | get_macro_indicators(). TTLCache 1hr | done |
| S3.3 | `specs/spec-S3.3-news-connector/` | S1.3 | `tools/news_connector.py` | NewsAPI wrapper + sentiment | get_news_sentiment(). Sentiment scoring. TTLCache 5min | done |
| S3.4 | `specs/spec-S3.4-sec-connector/` | S1.3 | `tools/sec_connector.py` | SEC Edgar wrapper + risk scoring | get_sec_filings(), score_risk(). BeautifulSoup parsing | done |
| S3.5 | `specs/spec-S3.5-technical-engine/` | -- | `tools/technical_engine.py` | Pure Python technical indicators | calc_rsi(), calc_macd(), calc_sma(), calc_volatility(). No external deps (numpy only) | done |

---

## Phase 4 -- ML Models

XGBoost signal fusion model and portfolio risk mathematics.

| Spec | Spec Location | Depends On | Location | Feature | Notes | Status |
|------|--------------|-----------|----------|---------|-------|--------|
| S4.1 | `specs/spec-S4.1-signal-fusion/` | S2.1, S2.2 | `models/signal_fusion.py` | XGBoost signal synthesis | SignalFusionModel class: fit(), predict(), extract_features(). Features from 5 AnalystReports. Returns FinalVerdict. Fallback to weighted-average if model not trained. Compliance hard override applied post-prediction | done |
| S4.2 | `specs/spec-S4.2-risk-calculator/` | S2.1 | `models/risk_calculator.py` | Portfolio risk math | calc_beta(), calc_sharpe(), calc_var_95(), calc_max_drawdown(), calc_position_size(). Pure math using numpy/pandas. Position size capped at 0.10 | done |
| S4.3 | `specs/spec-S4.3-model-persistence/` | S4.1 | `models/model_store.py` | Save/load XGBoost model | save_model(), load_model() using joblib. Model stored in data/models/. Version tracking with timestamp | done |

---

## Phase 5 -- Memory Layer

Persistent storage for analysis sessions and historical verdicts.

| Spec | Spec Location | Depends On | Location | Feature | Notes | Status |
|------|--------------|-----------|----------|---------|-------|--------|
| S5.1 | `specs/spec-S5.1-insight-vault/` | S1.3, S2.2 | `memory/insight_vault.py` | SQLite session storage | InsightVault class: store_verdict(), get_verdict(), list_verdicts(). aiosqlite for async. Auto-create tables on init. Schema: session_id, ticker, verdict_json, created_at | done |
| S5.2 | `specs/spec-S5.2-history-retriever/` | S5.1 | `memory/history_retriever.py` | Query past analyses | get_ticker_history(), get_signal_trend(), get_recent_verdicts(). Returns structured data for API endpoints | done |
| S5.3 | `specs/spec-S5.3-firestore-backend/` | S5.1 | `memory/firestore_vault.py` | Firestore backend (prod) | Same interface as InsightVault but backed by Firestore. Selected via ENVIRONMENT env var. Optional -- only needed for GCP deployment | done |

---

## Phase 6 -- Agent Framework

Base pattern for ADK agents and A2A server setup. This defines the template all specialist agents follow.

| Spec | Spec Location | Depends On | Location | Feature | Notes | Status |
|------|--------------|-----------|----------|---------|-------|--------|
| S6.1 | `specs/spec-S6.1-agent-base/` | S1.3, S2.1, S2.3 | `agents/base_agent.py` | ADK agent base class | BaseAnalystAgent: init with persona, tools, output schema. Standard analyze() method. Gemini client setup. Error handling wrapper. Agent card generation for A2A discovery | done |
| S6.2 | `specs/spec-S6.2-a2a-server/` | S6.1, S1.4 | `agents/a2a_server.py` | A2A protocol server factory | create_agent_server(): FastAPI app with /.well-known/agent-card.json endpoint, JSONRPC handler, health check. Reusable for all agents | done |

---

## Phase 7 -- Specialist Agents

Six domain-expert agents, each using the base pattern from Phase 6.

| Spec | Spec Location | Depends On | Location | Feature | Notes | Status |
|------|--------------|-----------|----------|---------|-------|--------|
| S7.1 | `specs/spec-S7.1-valuation-scout/` | S6.1, S3.1 | `agents/valuation_scout.py` | Fundamentals agent | Uses polygon_connector.get_fundamentals(). Returns ValuationReport. Calculates intrinsic_value_gap. Port 8001 | done |
| S7.2 | `specs/spec-S7.2-momentum-tracker/` | S6.1, S3.1, S3.5 | `agents/momentum_tracker.py` | Technical analysis agent | Uses polygon_connector + technical_engine. Returns MomentumReport. RSI, MACD, SMA crossovers. Port 8002 | done |
| S7.3 | `specs/spec-S7.3-pulse-monitor/` | S6.1, S3.3, S3.1 | `agents/pulse_monitor.py` | News sentiment agent | Uses news_connector + polygon news. Returns PulseReport. Caps confidence at 0.70 if <3 articles. Port 8003 | done |
| S7.4 | `specs/spec-S7.4-economy-watcher/` | S6.1, S3.2 | `agents/economy_watcher.py` | Macro indicators agent | Uses fred_connector. Returns EconomyReport. Classifies macro_regime. Port 8004 | done |
| S7.5 | `specs/spec-S7.5-compliance-checker/` | S6.1, S3.4 | `agents/compliance_checker.py` | Regulatory risk agent | Uses sec_connector. Returns ComplianceReport. going_concern/restatement flags. Port 8005 | done |
| S7.6 | `specs/spec-S7.6-risk-guardian/` | S6.1, S3.1, S4.2 | `agents/risk_guardian.py` | Portfolio risk agent | Uses polygon_connector + risk_calculator. Returns RiskGuardianReport. Position size capped at 0.10. Port 8007 | done |

---

## Phase 8 -- Orchestration

Signal synthesizer fuses analyst signals. Market conductor orchestrates all agents.

| Spec | Spec Location | Depends On | Location | Feature | Notes | Status |
|------|--------------|-----------|----------|---------|-------|--------|
| S8.1 | `specs/spec-S8.1-signal-synthesizer/` | S6.1, S4.1, S2.2 | `agents/signal_synthesizer.py` | Signal fusion agent | Receives 5 AnalystReports + RiskGuardianReport. Runs XGBoost prediction. Applies compliance override. Returns FinalVerdict. Port 8006 | done |
| S8.2 | `specs/spec-S8.2-market-conductor/` | S6.2, S7.1-S7.6, S8.1, S5.1 | `agents/market_conductor.py` | Orchestrator agent | Dispatches to all agents via asyncio.gather(). Handles timeouts (30s per agent). Reduces confidence for missing agents. Stores verdict in InsightVault. Port 8000 | done |
| S8.3 | `specs/spec-S8.3-portfolio-analyzer/` | S8.2, S2.2 | `agents/market_conductor.py` | Multi-stock portfolio analysis | analyze_portfolio(): runs analyze() for each ticker, aggregates into PortfolioInsight. Calculates diversification_score, selects top_pick | done |

---

## Phase 9 -- API Layer

FastAPI endpoints exposing the analysis system.

| Spec | Spec Location | Depends On | Location | Feature | Notes | Status |
|------|--------------|-----------|----------|---------|-------|--------|
| S9.1 | `specs/spec-S9.1-analyze-endpoint/` | S8.2, S1.4 | `app.py` | POST /analyze/{ticker} | Validates ticker format. Calls market_conductor.analyze(). Returns FinalVerdict JSON. Timeout: 60s | done |
| S9.2 | `specs/spec-S9.2-portfolio-endpoint/` | S8.3, S1.4 | `app.py` | POST /portfolio | Accepts list of tickers (max 10). Calls analyze_portfolio(). Returns PortfolioInsight JSON | done |
| S9.3 | `specs/spec-S9.3-history-endpoints/` | S5.2, S1.4 | `app.py` | GET /history/{ticker} + /history/{ticker}/trend | Returns past analyses and signal trends from InsightVault | done |
| S9.4 | `specs/spec-S9.4-error-handling/` | S9.1 | `app.py` | API error taxonomy | Custom exceptions: TickerNotFoundError, AnalysisTimeoutError, InsufficientDataError. Mapped to appropriate HTTP status codes. Structured error responses | done |

---

## Phase 10 -- Pipeline Integration

End-to-end wiring and integration testing.

| Spec | Spec Location | Depends On | Location | Feature | Notes | Status |
|------|--------------|-----------|----------|---------|-------|--------|
| S10.1 | `specs/spec-S10.1-pipeline-wiring/` | S9.1, S8.2, S5.1 | `app.py` | Full analysis pipeline | Wire: request -> conductor -> agents -> synthesizer -> vault -> response. All steps traced with session_id | done |
| S10.2 | `specs/spec-S10.2-graceful-degradation/` | S10.1 | `agents/market_conductor.py` | Agent failure handling | Missing agent -> reduce confidence by 0.20. Timeout handling. Partial results still returned with warning | done |
| S10.3 | `specs/spec-S10.3-integration-test/` | S10.1, S10.2 | `tests/test_pipeline.py` | Integration test: full pipeline | Mock all external services (Polygon, FRED, NewsAPI, SEC, Gemini). Submit analysis request. Assert: correct FinalVerdict structure, all agents called, verdict stored, response format correct | done |

---

## Phase 11 -- Infrastructure

Docker setup, scripts, and local development infrastructure.

| Spec | Spec Location | Depends On | Location | Feature | Notes | Status |
|------|--------------|-----------|----------|---------|-------|--------|
| S11.1 | `specs/spec-S11.1-dockerfile/` | S1.1 | `Dockerfile` | Multi-stage Dockerfile | Stage 1 (base): Python 3.12-slim, install deps. Stage 2 (dev): add pytest + ruff. Stage 3 (prod): copy app, non-root user, uvicorn CMD. Single container for all agents | done |
| S11.2 | `specs/spec-S11.2-docker-compose/` | S11.1 | `docker-compose.yml` | Local dev stack | Services: app (build from Dockerfile dev stage). Port 8000 exposed. Env from .env file. Volume mount for hot reload | done |
| S11.3 | `specs/spec-S11.3-launch-scripts/` | S1.2 | `scripts/launch_agents.sh`, `scripts/stop_agents.sh` | Agent launch/stop scripts | Start all agents on ports 8001-8007. PID management in .pids/. Health check after launch | done |
| S11.4 | `specs/spec-S11.4-dockerignore/` | -- | `.dockerignore` | Docker ignore rules | Exclude: venv, .env, notebooks/, docs/, __pycache__, *.pyc, .git, data/*.db, frontend/node_modules | done |
| S11.5 | `specs/spec-S11.5-health-check-script/` | S11.3 | `scripts/health_check.sh` | Health check for all agents | Curl each agent's /health endpoint. Report status table. Exit 1 if any agent is down | done |

---

## Phase 12 -- GCP Deployment

Cloud Run deployment with GitHub Actions CI/CD. Designed for under $50/month.

| Spec | Spec Location | Depends On | Location | Feature | Notes | Status |
|------|--------------|-----------|----------|---------|-------|--------|
| S12.1 | `specs/spec-S12.1-github-actions-ci/` | S1.2, S11.1 | `.github/workflows/ci.yml` | CI pipeline | On push/PR: checkout, setup Python, install deps, run tests (pytest), run lint (ruff). Fail fast on errors | pending |
| S12.2 | `specs/spec-S12.2-github-actions-cd/` | S12.1, S11.1 | `.github/workflows/deploy.yml` | CD pipeline | On push to main: build Docker image, push to Artifact Registry, deploy to Cloud Run. Uses Workload Identity Federation (no service account keys) | pending |
| S12.3 | `specs/spec-S12.3-cloud-run-config/` | S11.1 | `deploy/cloudrun.yaml` | Cloud Run service config | Single container. Memory: 1GB. CPU: 1. Min instances: 0. Max instances: 4. Port: 8080. Concurrency: 80. Timeout: 300s | pending |
| S12.4 | `specs/spec-S12.4-secret-manager/` | S1.3 | `deploy/setup-secrets.sh` | GCP Secret Manager setup | Script to create secrets: GOOGLE_API_KEY, POLYGON_API_KEY, FRED_API_KEY, NEWS_API_KEY. Cloud Run mounts as env vars | pending |
| S12.5 | `specs/spec-S12.5-firestore-setup/` | S5.3 | `deploy/setup-firestore.sh` | Firestore database setup | Create Firestore database in Native mode. Collection: verdicts. Composite index on ticker + created_at | pending |

---

## Phase 13 -- Frontend

Next.js dashboard for stock analysis visualization.

| Spec | Spec Location | Depends On | Location | Feature | Notes | Status |
|------|--------------|-----------|----------|---------|-------|--------|
| S13.1 | `specs/spec-S13.1-nextjs-scaffold/` | S9.1 | `frontend/` | Next.js project setup | Create Next.js app with TypeScript + Tailwind. API proxy to backend. Environment config | done |
| S13.2 | `specs/spec-S13.2-analysis-page/` | S13.1, S9.1 | `frontend/app/page.tsx` | Stock analysis page | Ticker input, submit button, loading state. Display FinalVerdict with signal badge, confidence meter, key drivers | done |
| S13.3 | `specs/spec-S13.3-agent-cards/` | S13.2 | `frontend/app/components/` | Agent signal cards | Individual cards for each agent showing signal, confidence, key metrics. Color-coded BUY/HOLD/SELL | done |
| S13.4 | `specs/spec-S13.4-history-view/` | S13.1, S9.3 | `frontend/app/history/` | Analysis history page | Past analyses for a ticker. Signal trend chart over time. Filterable by date range | done |

---

## Phase 15 -- Enhanced UX

Backend enhancements (ticker search, rich response, better prompts) and complete frontend redesign with dark glassmorphism theme.

| Spec | Spec Location | Depends On | Location | Feature | Notes | Status |
|------|--------------|-----------|----------|---------|-------|--------|
| S15.1 | `specs/spec-S15.1-ticker-search/` | S1.3, S3.1 | `tools/ticker_search.py`, `api/routes.py` | Ticker search/autocomplete API | Polygon ticker search, 1hr TTL cache, GET /api/v1/search?q= | done |
| S15.2 | `specs/spec-S15.2-rich-analysis-response/` | S8.2, S2.2 | `config/data_contracts.py`, `agents/market_conductor.py` | Rich analysis response | AgentDetail model, risk_level, execution_time_ms, per-agent metrics | done |
| S15.3 | `specs/spec-S15.3-enhanced-prompts/` | S2.3 | `config/analyst_personas.py` | Enhanced agent prompts | Better signal guidelines, confidence criteria, decision logic | done |
| S15.4 | `specs/spec-S15.4-dark-design-system/` | S13.1 | `frontend/` | Dark glassmorphism design system | Framer Motion, glass cards, gradient accents, glow effects | done |
| S15.5 | `specs/spec-S15.5-ticker-autocomplete/` | S15.1, S15.4 | `frontend/components/TickerSearch.tsx` | Ticker autocomplete component | Debounced search, dropdown, keyboard nav, popular stocks | done |
| S15.6 | `specs/spec-S15.6-analysis-dashboard/` | S15.2, S15.4, S15.5 | `frontend/app/page.tsx` | Analysis dashboard redesign | Orchestrator card, rich agent cards, results panel, animations | done |
| S15.7 | `specs/spec-S15.7-history-redesign/` | S15.4, S9.3 | `frontend/app/history/` | History page redesign | Stats bar, filter tabs, rich rows, detail modal | done |

---

## Phase 14 -- Evaluation & QA

Evaluation framework, backtesting, and end-to-end validation.

| Spec | Spec Location | Depends On | Location | Feature | Notes | Status |
|------|--------------|-----------|----------|---------|-------|--------|
| S14.1 | `specs/spec-S14.1-quality-assessor/` | S10.1 | `evaluation/quality_assessor.py` | Quality scoring for verdicts | Score analysis quality: data completeness, signal consensus, confidence calibration. Returns quality grade A-F | done |
| S14.2 | `specs/spec-S14.2-benchmark-cases/` | S14.1 | `evaluation/benchmarks/` | Benchmark test cases | 10 well-known stocks with expected signal ranges. AAPL, TSLA, JPM, etc. Validate agent signals are reasonable | done |
| S14.3 | `specs/spec-S14.3-backtester/` | S14.2, S5.2 | `evaluation/backtester.py` | Historical backtesting | Run analysis on historical data. Compare predicted signals vs actual price movement. Track accuracy metrics | done |
| S14.4 | `specs/spec-S14.4-e2e-smoke-test/` | S10.1 | `tests/test_e2e.py` | End-to-end smoke test | Full analysis of AAPL with all real APIs (or mocked). Assert complete FinalVerdict returned in <30s | done |
| S14.5 | `specs/spec-S14.5-documentation/` | S10.3 | `README.md`, `docs/` | Final documentation | README: local setup, running tests, deployment guide. API docs. Architecture diagrams | done |

---

## Phase 16 -- Intelligence Layer

Cross-session learning, conversational AI interface, and prediction accuracy tracking. Transforms EquityIQ from a stateless analyzer to a learning system.

| Spec | Spec Location | Depends On | Location | Feature | Notes | Status |
|------|--------------|-----------|----------|---------|-------|--------|
| S16.1 | `specs/spec-S16.1-vertex-memory-bank/` | S5.3, S8.2 | `memory/vertex_memory.py` | Vertex AI Memory Bank | Cross-session conversational memory using Vertex AI. Stores user preferences, past interactions, prediction outcomes. Enables the system to learn from historical predictions and improve signal weights over time | done |
| S16.2 | `specs/spec-S16.2-natural-language-chat/` | S16.1, S9.1, S13.1 | `api/chat.py`, `frontend/app/chat/` | Natural language chat interface | POST /api/v1/chat endpoint with Gemini streaming. Conversation history management. Context-aware follow-ups ("Why did you say SELL?", "Compare AAPL vs MSFT"). Frontend chat panel with message bubbles. Uses agent results as grounding context | done |
| S16.3 | `specs/spec-S16.3-prediction-tracker/` | S5.2, S14.3 | `evaluation/prediction_tracker.py` | Prediction accuracy tracker | Compare past FinalVerdicts to actual price movement (30/60/90 day windows). Track hit rate per agent and overall. Auto-adjust signal weights based on historical accuracy. Dashboard showing prediction scorecard | done |

---

## Phase 17 -- Integrations

Broker connectivity, portfolio synchronization, and alert system. Connects EquityIQ to the trading workflow.

| Spec | Spec Location | Depends On | Location | Feature | Notes | Status |
|------|--------------|-----------|----------|---------|-------|--------|
| S17.1 | `specs/spec-S17.1-zerodha-integration/` | S9.2, S8.3 | `integrations/zerodha.py` | Zerodha broker integration (India) | OAuth2 login via Kite Connect API. Fetch holdings and positions. Display portfolio with live P&L. Map Zerodha symbols to EquityIQ tickers (.NS/.BO). Read-only initially -- no order placement | pending |
| S17.2 | `specs/spec-S17.2-alpaca-integration/` | S9.2, S8.3 | `integrations/alpaca.py` | Alpaca broker integration (US) | OAuth2 + API key auth. Paper trading support. Fetch positions and account balance. Map Alpaca symbols to EquityIQ tickers. Optional: place paper orders based on STRONG_BUY/STRONG_SELL signals | pending |
| S17.3 | `specs/spec-S17.3-portfolio-sync/` | S17.1, S17.2, S8.3 | `integrations/portfolio_sync.py` | Portfolio sync from brokers | Auto-import holdings from connected Zerodha/Alpaca accounts. Run analyze_portfolio() on imported tickers. Show side-by-side: current holdings vs EquityIQ recommendations. Periodic refresh (configurable interval) | pending |
| S17.4 | `specs/spec-S17.4-webhook-alerts/` | S10.1, S5.1 | `integrations/alerts.py`, `api/webhooks.py` | Webhook and alert system | Watch list: user adds tickers to monitor. Background scheduler re-analyzes watched tickers daily. Signal change detection: notify when verdict changes (e.g., BUY -> SELL). Webhook delivery (POST to user-configured URL). Optional: email via SendGrid or Telegram bot integration | pending |

---

## Master Spec Index

| Spec | Phase | Location | Feature | Spec Location | Status |
|------|-------|----------|---------|--------------|--------|
| S1.1 | Project Foundation | `pyproject.toml`, `.env.example` | Dependency declaration | `specs/spec-S1.1-dependency-declaration/` | done |
| S1.2 | Project Foundation | `Makefile` | Developer commands | `specs/spec-S1.2-developer-commands/` | done |
| S1.3 | Project Foundation | `config/settings.py` | pydantic-settings config | `specs/spec-S1.3-pydantic-settings/` | done |
| S1.4 | Project Foundation | `app.py` | FastAPI app factory | `specs/spec-S1.4-fastapi-skeleton/` | done |
| S1.5 | Project Foundation | `config/logging.py` | Structured logging | `specs/spec-S1.5-logging-setup/` | done |
| S2.1 | Data Contracts | `config/data_contracts.py` | AnalystReport + 6 subclass schemas | `specs/spec-S2.1-analyst-report-schemas/` | done |
| S2.2 | Data Contracts | `config/data_contracts.py` | FinalVerdict + PortfolioInsight | `specs/spec-S2.2-verdict-schemas/` | done |
| S2.3 | Data Contracts | `config/analyst_personas.py` | Agent system prompts | `specs/spec-S2.3-agent-personas/` | done |
| S3.1 | Data Connectors | `tools/polygon_connector.py` | Polygon.io async wrapper | `specs/spec-S3.1-polygon-connector/` | done |
| S3.2 | Data Connectors | `tools/fred_connector.py` | FRED API async wrapper | `specs/spec-S3.2-fred-connector/` | done |
| S3.3 | Data Connectors | `tools/news_connector.py` | NewsAPI + sentiment | `specs/spec-S3.3-news-connector/` | done |
| S3.4 | Data Connectors | `tools/sec_connector.py` | SEC Edgar + risk scoring | `specs/spec-S3.4-sec-connector/` | done |
| S3.5 | Data Connectors | `tools/technical_engine.py` | Technical indicators | `specs/spec-S3.5-technical-engine/` | done |
| S4.1 | ML Models | `models/signal_fusion.py` | XGBoost signal synthesis | `specs/spec-S4.1-signal-fusion/` | done |
| S4.2 | ML Models | `models/risk_calculator.py` | Portfolio risk math | `specs/spec-S4.2-risk-calculator/` | done |
| S4.3 | ML Models | `models/model_store.py` | Model persistence | `specs/spec-S4.3-model-persistence/` | done |
| S5.1 | Memory Layer | `memory/insight_vault.py` | SQLite session storage | `specs/spec-S5.1-insight-vault/` | done |
| S5.2 | Memory Layer | `memory/history_retriever.py` | Query past analyses | `specs/spec-S5.2-history-retriever/` | done |
| S5.3 | Memory Layer | `memory/firestore_vault.py` | Firestore backend (prod) | `specs/spec-S5.3-firestore-backend/` | done |
| S6.1 | Agent Framework | `agents/base_agent.py` | ADK agent base class | `specs/spec-S6.1-agent-base/` | done |
| S6.2 | Agent Framework | `agents/a2a_server.py` | A2A protocol server factory | `specs/spec-S6.2-a2a-server/` | done |
| S7.1 | Specialist Agents | `agents/valuation_scout.py` | Fundamentals agent | `specs/spec-S7.1-valuation-scout/` | done |
| S7.2 | Specialist Agents | `agents/momentum_tracker.py` | Technical analysis agent | `specs/spec-S7.2-momentum-tracker/` | done |
| S7.3 | Specialist Agents | `agents/pulse_monitor.py` | News sentiment agent | `specs/spec-S7.3-pulse-monitor/` | done |
| S7.4 | Specialist Agents | `agents/economy_watcher.py` | Macro indicators agent | `specs/spec-S7.4-economy-watcher/` | done |
| S7.5 | Specialist Agents | `agents/compliance_checker.py` | Regulatory risk agent | `specs/spec-S7.5-compliance-checker/` | done |
| S7.6 | Specialist Agents | `agents/risk_guardian.py` | Portfolio risk agent | `specs/spec-S7.6-risk-guardian/` | done |
| S8.1 | Orchestration | `agents/signal_synthesizer.py` | Signal fusion agent | `specs/spec-S8.1-signal-synthesizer/` | done |
| S8.2 | Orchestration | `agents/market_conductor.py` | Orchestrator agent | `specs/spec-S8.2-market-conductor/` | done |
| S8.3 | Orchestration | `agents/market_conductor.py` | Portfolio analysis | `specs/spec-S8.3-portfolio-analyzer/` | done |
| S9.1 | API Layer | `app.py` | POST /analyze/{ticker} | `specs/spec-S9.1-analyze-endpoint/` | done |
| S9.2 | API Layer | `app.py` | POST /portfolio | `specs/spec-S9.2-portfolio-endpoint/` | done |
| S9.3 | API Layer | `app.py` | GET /history endpoints | `specs/spec-S9.3-history-endpoints/` | done |
| S9.4 | API Layer | `app.py` | Error taxonomy | `specs/spec-S9.4-error-handling/` | done |
| S10.1 | Pipeline Integration | `app.py` | Full pipeline wiring | `specs/spec-S10.1-pipeline-wiring/` | done |
| S10.2 | Pipeline Integration | `agents/market_conductor.py` | Graceful degradation | `specs/spec-S10.2-graceful-degradation/` | done |
| S10.3 | Pipeline Integration | `tests/test_pipeline.py` | Integration test | `specs/spec-S10.3-integration-test/` | done |
| S11.1 | Infrastructure | `Dockerfile` | Multi-stage Dockerfile | `specs/spec-S11.1-dockerfile/` | done |
| S11.2 | Infrastructure | `docker-compose.yml` | Local dev stack | `specs/spec-S11.2-docker-compose/` | done |
| S11.3 | Infrastructure | `scripts/launch_agents.sh` | Launch/stop scripts | `specs/spec-S11.3-launch-scripts/` | done |
| S11.4 | Infrastructure | `.dockerignore` | Docker ignore rules | `specs/spec-S11.4-dockerignore/` | done |
| S11.5 | Infrastructure | `scripts/health_check.sh` | Health check script | `specs/spec-S11.5-health-check-script/` | done |
| S12.1 | GCP Deployment | `.github/workflows/ci.yml` | CI pipeline | `specs/spec-S12.1-github-actions-ci/` | pending |
| S12.2 | GCP Deployment | `.github/workflows/deploy.yml` | CD pipeline | `specs/spec-S12.2-github-actions-cd/` | pending |
| S12.3 | GCP Deployment | `deploy/cloudrun.yaml` | Cloud Run config | `specs/spec-S12.3-cloud-run-config/` | pending |
| S12.4 | GCP Deployment | `deploy/setup-secrets.sh` | Secret Manager setup | `specs/spec-S12.4-secret-manager/` | pending |
| S12.5 | GCP Deployment | `deploy/setup-firestore.sh` | Firestore setup | `specs/spec-S12.5-firestore-setup/` | pending |
| S13.1 | Frontend | `frontend/` | Next.js scaffold | `specs/spec-S13.1-nextjs-scaffold/` | done |
| S13.2 | Frontend | `frontend/app/page.tsx` | Analysis page | `specs/spec-S13.2-analysis-page/` | done |
| S13.3 | Frontend | `frontend/app/components/` | Agent signal cards | `specs/spec-S13.3-agent-cards/` | done |
| S13.4 | Frontend | `frontend/app/history/` | History view | `specs/spec-S13.4-history-view/` | done |
| S14.1 | Evaluation & QA | `evaluation/quality_assessor.py` | Quality scoring | `specs/spec-S14.1-quality-assessor/` | done |
| S14.2 | Evaluation & QA | `evaluation/benchmarks/` | Benchmark cases | `specs/spec-S14.2-benchmark-cases/` | done |
| S14.3 | Evaluation & QA | `evaluation/backtester.py` | Backtesting | `specs/spec-S14.3-backtester/` | done |
| S14.4 | Evaluation & QA | `tests/test_e2e.py` | E2E smoke test | `specs/spec-S14.4-e2e-smoke-test/` | done |
| S14.5 | Evaluation & QA | `README.md`, `docs/` | Documentation | `specs/spec-S14.5-documentation/` | done |
| S15.1 | Enhanced UX | `tools/ticker_search.py`, `api/routes.py` | Ticker search API | `specs/spec-S15.1-ticker-search/` | done |
| S15.2 | Enhanced UX | `config/data_contracts.py`, `agents/market_conductor.py` | Rich analysis response | `specs/spec-S15.2-rich-analysis-response/` | done |
| S15.3 | Enhanced UX | `config/analyst_personas.py` | Enhanced agent prompts | `specs/spec-S15.3-enhanced-prompts/` | done |
| S15.4 | Enhanced UX | `frontend/` | Dark design system | `specs/spec-S15.4-dark-design-system/` | done |
| S15.5 | Enhanced UX | `frontend/components/TickerSearch.tsx` | Ticker autocomplete | `specs/spec-S15.5-ticker-autocomplete/` | done |
| S15.6 | Enhanced UX | `frontend/app/page.tsx` | Analysis dashboard redesign | `specs/spec-S15.6-analysis-dashboard/` | done |
| S15.7 | Enhanced UX | `frontend/app/history/` | History page redesign | `specs/spec-S15.7-history-redesign/` | done |
| S16.1 | Intelligence Layer | `memory/vertex_memory.py` | Vertex AI Memory Bank | `specs/spec-S16.1-vertex-memory-bank/` | done |
| S16.2 | Intelligence Layer | `api/chat.py`, `frontend/app/chat/` | Natural language chat | `specs/spec-S16.2-natural-language-chat/` | done |
| S16.3 | Intelligence Layer | `evaluation/prediction_tracker.py` | Prediction accuracy tracker | `specs/spec-S16.3-prediction-tracker/` | done |
| S17.1 | Integrations | `integrations/zerodha.py` | Zerodha broker (India) | `specs/spec-S17.1-zerodha-integration/` | pending |
| S17.2 | Integrations | `integrations/alpaca.py` | Alpaca broker (US) | `specs/spec-S17.2-alpaca-integration/` | pending |
| S17.3 | Integrations | `integrations/portfolio_sync.py` | Portfolio sync | `specs/spec-S17.3-portfolio-sync/` | pending |
| S17.4 | Integrations | `integrations/alerts.py`, `api/webhooks.py` | Webhook alerts | `specs/spec-S17.4-webhook-alerts/` | pending |
