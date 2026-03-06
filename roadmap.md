# Roadmap -- EquityIQ: Multi-Agent Stock Intelligence System

**Prototype target**: End-to-end stock analysis via API -- 7 agents in parallel, XGBoost synthesis, final verdict.
**Budget**: $0-50 GCP (free tier + minimal paid).
**LLM**: Gemini 3 Flash (`gemini-3-flash-preview`) for all agents.
**Out of scope for prototype**: Real-time streaming, multi-market (non-US), mobile app, social trading features.

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

---

## Phase 1 -- Project Foundation

Bootstraps the project: dependency declaration, environment config, app factory, Makefile, testing/linting setup.
Output: `make local-dev` starts a healthy FastAPI server with `/health` endpoint.

| Spec | Spec Location | Depends On | Location | Feature | Notes | Status |
|------|--------------|-----------|----------|---------|-------|--------|
| S1.1 | `specs/spec-S1.1-dependency-declaration/` | -- | `pyproject.toml`, `.env.example` | Dependency declaration | Runtime: google-adk, google-generativeai, fastapi, uvicorn, pydantic, pydantic-settings, httpx, aiohttp, cachetools, aiosqlite, xgboost, scikit-learn, pandas, numpy, python-dotenv, beautifulsoup4, lxml, colorlog. Dev: pytest, pytest-asyncio, ruff, pytest-mock, httpx | pending |
| S1.2 | `specs/spec-S1.2-developer-commands/` | -- | `Makefile` | Developer commands | Targets: venv, install, install-dev, local-dev, local-test, local-lint, dev (Docker), test (Docker) | pending |
| S1.3 | `specs/spec-S1.3-pydantic-settings/` | S1.1 | `config/settings.py` | Settings via pydantic-settings | Fields: GOOGLE_API_KEY, POLYGON_API_KEY, FRED_API_KEY, NEWS_API_KEY, ENVIRONMENT, SQLITE_DB_PATH, GCP_PROJECT_ID, GCP_REGION, LOG_LEVEL. All from .env | pending |
| S1.4 | `specs/spec-S1.4-fastapi-skeleton/` | S1.3 | `app.py` | FastAPI app factory | Lifespan: connect DB on startup, disconnect on shutdown. GET /health returning `{"status": "ok", "agents": {...}}`. Include routers | pending |
| S1.5 | `specs/spec-S1.5-logging-setup/` | S1.3 | `config/logging.py` | Structured logging | Colorlog for local, structured JSON for production. LOG_LEVEL from settings. request_id context for tracing | pending |

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

Async API wrappers for all external data sources. TTL caching on every call. Already implemented -- bring under spec governance.

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
| S4.1 | `specs/spec-S4.1-signal-fusion/` | S2.1, S2.2 | `models/signal_fusion.py` | XGBoost signal synthesis | SignalFusionModel class: fit(), predict(), extract_features(). Features from 5 AnalystReports. Returns FinalVerdict. Fallback to weighted-average if model not trained. Compliance hard override applied post-prediction | pending |
| S4.2 | `specs/spec-S4.2-risk-calculator/` | S2.1 | `models/risk_calculator.py` | Portfolio risk math | calc_beta(), calc_sharpe(), calc_var_95(), calc_max_drawdown(), calc_position_size(). Pure math using numpy/pandas. Position size capped at 0.10 | pending |
| S4.3 | `specs/spec-S4.3-model-persistence/` | S4.1 | `models/model_store.py` | Save/load XGBoost model | save_model(), load_model() using joblib. Model stored in data/models/. Version tracking with timestamp | pending |

---

## Phase 5 -- Memory Layer

Persistent storage for analysis sessions and historical verdicts.

| Spec | Spec Location | Depends On | Location | Feature | Notes | Status |
|------|--------------|-----------|----------|---------|-------|--------|
| S5.1 | `specs/spec-S5.1-insight-vault/` | S1.3, S2.2 | `memory/insight_vault.py` | SQLite session storage | InsightVault class: store_verdict(), get_verdict(), list_verdicts(). aiosqlite for async. Auto-create tables on init. Schema: session_id, ticker, verdict_json, created_at | pending |
| S5.2 | `specs/spec-S5.2-history-retriever/` | S5.1 | `memory/history_retriever.py` | Query past analyses | get_ticker_history(), get_signal_trend(), get_recent_verdicts(). Returns structured data for API endpoints | pending |
| S5.3 | `specs/spec-S5.3-firestore-backend/` | S5.1 | `memory/firestore_vault.py` | Firestore backend (prod) | Same interface as InsightVault but backed by Firestore. Selected via ENVIRONMENT env var. Optional -- only needed for GCP deployment | pending |

---

## Phase 6 -- Agent Framework

Base pattern for ADK agents and A2A server setup. This defines the template all specialist agents follow.

| Spec | Spec Location | Depends On | Location | Feature | Notes | Status |
|------|--------------|-----------|----------|---------|-------|--------|
| S6.1 | `specs/spec-S6.1-agent-base/` | S1.3, S2.1, S2.3 | `agents/base_agent.py` | ADK agent base class | BaseAnalystAgent: init with persona, tools, output schema. Standard analyze() method. Gemini client setup. Error handling wrapper. Agent card generation for A2A discovery | pending |
| S6.2 | `specs/spec-S6.2-a2a-server/` | S6.1, S1.4 | `agents/a2a_server.py` | A2A protocol server factory | create_agent_server(): FastAPI app with /.well-known/agent-card.json endpoint, JSONRPC handler, health check. Reusable for all agents | pending |

---

## Phase 7 -- Specialist Agents

Six domain-expert agents, each using the base pattern from Phase 6.

| Spec | Spec Location | Depends On | Location | Feature | Notes | Status |
|------|--------------|-----------|----------|---------|-------|--------|
| S7.1 | `specs/spec-S7.1-valuation-scout/` | S6.1, S3.1 | `agents/valuation_scout.py` | Fundamentals agent | Uses polygon_connector.get_fundamentals(). Returns ValuationReport. Calculates intrinsic_value_gap. Port 8001 | pending |
| S7.2 | `specs/spec-S7.2-momentum-tracker/` | S6.1, S3.1, S3.5 | `agents/momentum_tracker.py` | Technical analysis agent | Uses polygon_connector + technical_engine. Returns MomentumReport. RSI, MACD, SMA crossovers. Port 8002 | pending |
| S7.3 | `specs/spec-S7.3-pulse-monitor/` | S6.1, S3.3, S3.1 | `agents/pulse_monitor.py` | News sentiment agent | Uses news_connector + polygon news. Returns PulseReport. Caps confidence at 0.70 if <3 articles. Port 8003 | pending |
| S7.4 | `specs/spec-S7.4-economy-watcher/` | S6.1, S3.2 | `agents/economy_watcher.py` | Macro indicators agent | Uses fred_connector. Returns EconomyReport. Classifies macro_regime. Port 8004 | pending |
| S7.5 | `specs/spec-S7.5-compliance-checker/` | S6.1, S3.4 | `agents/compliance_checker.py` | Regulatory risk agent | Uses sec_connector. Returns ComplianceReport. going_concern/restatement flags. Port 8005 | pending |
| S7.6 | `specs/spec-S7.6-risk-guardian/` | S6.1, S3.1, S4.2 | `agents/risk_guardian.py` | Portfolio risk agent | Uses polygon_connector + risk_calculator. Returns RiskGuardianReport. Position size capped at 0.10. Port 8007 | pending |

---

## Phase 8 -- Orchestration

Signal synthesizer fuses analyst signals. Market conductor orchestrates all agents.

| Spec | Spec Location | Depends On | Location | Feature | Notes | Status |
|------|--------------|-----------|----------|---------|-------|--------|
| S8.1 | `specs/spec-S8.1-signal-synthesizer/` | S6.1, S4.1, S2.2 | `agents/signal_synthesizer.py` | Signal fusion agent | Receives 5 AnalystReports + RiskGuardianReport. Runs XGBoost prediction. Applies compliance override. Returns FinalVerdict. Port 8006 | pending |
| S8.2 | `specs/spec-S8.2-market-conductor/` | S6.2, S7.1-S7.6, S8.1, S5.1 | `agents/market_conductor.py` | Orchestrator agent | Dispatches to all agents via asyncio.gather(). Handles timeouts (30s per agent). Reduces confidence for missing agents. Stores verdict in InsightVault. Port 8000 | pending |
| S8.3 | `specs/spec-S8.3-portfolio-analyzer/` | S8.2, S2.2 | `agents/market_conductor.py` | Multi-stock portfolio analysis | analyze_portfolio(): runs analyze() for each ticker, aggregates into PortfolioInsight. Calculates diversification_score, selects top_pick | pending |

---

## Phase 9 -- API Layer

FastAPI endpoints exposing the analysis system.

| Spec | Spec Location | Depends On | Location | Feature | Notes | Status |
|------|--------------|-----------|----------|---------|-------|--------|
| S9.1 | `specs/spec-S9.1-analyze-endpoint/` | S8.2, S1.4 | `app.py` | POST /analyze/{ticker} | Validates ticker format. Calls market_conductor.analyze(). Returns FinalVerdict JSON. Timeout: 60s | pending |
| S9.2 | `specs/spec-S9.2-portfolio-endpoint/` | S8.3, S1.4 | `app.py` | POST /portfolio | Accepts list of tickers (max 10). Calls analyze_portfolio(). Returns PortfolioInsight JSON | pending |
| S9.3 | `specs/spec-S9.3-history-endpoints/` | S5.2, S1.4 | `app.py` | GET /history/{ticker} + /history/{ticker}/trend | Returns past analyses and signal trends from InsightVault | pending |
| S9.4 | `specs/spec-S9.4-error-handling/` | S9.1 | `app.py` | API error taxonomy | Custom exceptions: TickerNotFoundError, AnalysisTimeoutError, InsufficientDataError. Mapped to appropriate HTTP status codes. Structured error responses | pending |

---

## Phase 10 -- Pipeline Integration

End-to-end wiring and integration testing.

| Spec | Spec Location | Depends On | Location | Feature | Notes | Status |
|------|--------------|-----------|----------|---------|-------|--------|
| S10.1 | `specs/spec-S10.1-pipeline-wiring/` | S9.1, S8.2, S5.1 | `app.py` | Full analysis pipeline | Wire: request -> conductor -> agents -> synthesizer -> vault -> response. All steps traced with session_id | pending |
| S10.2 | `specs/spec-S10.2-graceful-degradation/` | S10.1 | `agents/market_conductor.py` | Agent failure handling | Missing agent -> reduce confidence by 0.20. Timeout handling. Partial results still returned with warning | pending |
| S10.3 | `specs/spec-S10.3-integration-test/` | S10.1, S10.2 | `tests/test_pipeline.py` | Integration test: full pipeline | Mock all external services (Polygon, FRED, NewsAPI, SEC, Gemini). Submit analysis request. Assert: correct FinalVerdict structure, all agents called, verdict stored, response format correct | pending |

---

## Phase 11 -- Infrastructure

Docker setup, scripts, and local development infrastructure.

| Spec | Spec Location | Depends On | Location | Feature | Notes | Status |
|------|--------------|-----------|----------|---------|-------|--------|
| S11.1 | `specs/spec-S11.1-dockerfile/` | S1.1 | `Dockerfile` | Multi-stage Dockerfile | Stage 1 (base): Python 3.12-slim, install deps. Stage 2 (dev): add pytest + ruff. Stage 3 (prod): copy app, non-root user, uvicorn CMD. Single container for all agents | pending |
| S11.2 | `specs/spec-S11.2-docker-compose/` | S11.1 | `docker-compose.yml` | Local dev stack | Services: app (build from Dockerfile dev stage). Port 8000 exposed. Env from .env file. Volume mount for hot reload | pending |
| S11.3 | `specs/spec-S11.3-launch-scripts/` | S1.2 | `scripts/launch_agents.sh`, `scripts/stop_agents.sh` | Agent launch/stop scripts | Start all agents on ports 8001-8007. PID management in .pids/. Health check after launch | pending |
| S11.4 | `specs/spec-S11.4-dockerignore/` | -- | `.dockerignore` | Docker ignore rules | Exclude: venv, .env, notebooks/, docs/, __pycache__, *.pyc, .git, data/*.db, frontend/node_modules | pending |
| S11.5 | `specs/spec-S11.5-health-check-script/` | S11.3 | `scripts/health_check.sh` | Health check for all agents | Curl each agent's /health endpoint. Report status table. Exit 1 if any agent is down | pending |

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
| S13.1 | `specs/spec-S13.1-nextjs-scaffold/` | S9.1 | `frontend/` | Next.js project setup | Create Next.js app with TypeScript + Tailwind. API proxy to backend. Environment config | pending |
| S13.2 | `specs/spec-S13.2-analysis-page/` | S13.1, S9.1 | `frontend/app/page.tsx` | Stock analysis page | Ticker input, submit button, loading state. Display FinalVerdict with signal badge, confidence meter, key drivers | pending |
| S13.3 | `specs/spec-S13.3-agent-cards/` | S13.2 | `frontend/app/components/` | Agent signal cards | Individual cards for each agent showing signal, confidence, key metrics. Color-coded BUY/HOLD/SELL | pending |
| S13.4 | `specs/spec-S13.4-history-view/` | S13.1, S9.3 | `frontend/app/history/` | Analysis history page | Past analyses for a ticker. Signal trend chart over time. Filterable by date range | pending |

---

## Phase 14 -- Evaluation & QA

Evaluation framework, backtesting, and end-to-end validation.

| Spec | Spec Location | Depends On | Location | Feature | Notes | Status |
|------|--------------|-----------|----------|---------|-------|--------|
| S14.1 | `specs/spec-S14.1-quality-assessor/` | S10.1 | `evaluation/quality_assessor.py` | Quality scoring for verdicts | Score analysis quality: data completeness, signal consensus, confidence calibration. Returns quality grade A-F | pending |
| S14.2 | `specs/spec-S14.2-benchmark-cases/` | S14.1 | `evaluation/benchmarks/` | Benchmark test cases | 10 well-known stocks with expected signal ranges. AAPL, TSLA, JPM, etc. Validate agent signals are reasonable | pending |
| S14.3 | `specs/spec-S14.3-backtester/` | S14.2, S5.2 | `evaluation/backtester.py` | Historical backtesting | Run analysis on historical data. Compare predicted signals vs actual price movement. Track accuracy metrics | pending |
| S14.4 | `specs/spec-S14.4-e2e-smoke-test/` | S10.1 | `tests/test_e2e.py` | End-to-end smoke test | Full analysis of AAPL with all real APIs (or mocked). Assert complete FinalVerdict returned in <30s | pending |
| S14.5 | `specs/spec-S14.5-documentation/` | S10.3 | `README.md`, `docs/` | Final documentation | README: local setup, running tests, deployment guide. API docs. Architecture diagrams | pending |

---

## Master Spec Index

| Spec | Phase | Location | Feature | Spec Location | Status |
|------|-------|----------|---------|--------------|--------|
| S1.1 | Project Foundation | `pyproject.toml`, `.env.example` | Dependency declaration | `specs/spec-S1.1-dependency-declaration/` | pending |
| S1.2 | Project Foundation | `Makefile` | Developer commands | `specs/spec-S1.2-developer-commands/` | pending |
| S1.3 | Project Foundation | `config/settings.py` | pydantic-settings config | `specs/spec-S1.3-pydantic-settings/` | pending |
| S1.4 | Project Foundation | `app.py` | FastAPI app factory | `specs/spec-S1.4-fastapi-skeleton/` | pending |
| S1.5 | Project Foundation | `config/logging.py` | Structured logging | `specs/spec-S1.5-logging-setup/` | pending |
| S2.1 | Data Contracts | `config/data_contracts.py` | AnalystReport + 6 subclass schemas | `specs/spec-S2.1-analyst-report-schemas/` | done |
| S2.2 | Data Contracts | `config/data_contracts.py` | FinalVerdict + PortfolioInsight | `specs/spec-S2.2-verdict-schemas/` | done |
| S2.3 | Data Contracts | `config/analyst_personas.py` | Agent system prompts | `specs/spec-S2.3-agent-personas/` | done |
| S3.1 | Data Connectors | `tools/polygon_connector.py` | Polygon.io async wrapper | `specs/spec-S3.1-polygon-connector/` | done |
| S3.2 | Data Connectors | `tools/fred_connector.py` | FRED API async wrapper | `specs/spec-S3.2-fred-connector/` | done |
| S3.3 | Data Connectors | `tools/news_connector.py` | NewsAPI + sentiment | `specs/spec-S3.3-news-connector/` | done |
| S3.4 | Data Connectors | `tools/sec_connector.py` | SEC Edgar + risk scoring | `specs/spec-S3.4-sec-connector/` | done |
| S3.5 | Data Connectors | `tools/technical_engine.py` | Technical indicators | `specs/spec-S3.5-technical-engine/` | done |
| S4.1 | ML Models | `models/signal_fusion.py` | XGBoost signal synthesis | `specs/spec-S4.1-signal-fusion/` | pending |
| S4.2 | ML Models | `models/risk_calculator.py` | Portfolio risk math | `specs/spec-S4.2-risk-calculator/` | pending |
| S4.3 | ML Models | `models/model_store.py` | Model persistence | `specs/spec-S4.3-model-persistence/` | pending |
| S5.1 | Memory Layer | `memory/insight_vault.py` | SQLite session storage | `specs/spec-S5.1-insight-vault/` | pending |
| S5.2 | Memory Layer | `memory/history_retriever.py` | Query past analyses | `specs/spec-S5.2-history-retriever/` | pending |
| S5.3 | Memory Layer | `memory/firestore_vault.py` | Firestore backend (prod) | `specs/spec-S5.3-firestore-backend/` | pending |
| S6.1 | Agent Framework | `agents/base_agent.py` | ADK agent base class | `specs/spec-S6.1-agent-base/` | pending |
| S6.2 | Agent Framework | `agents/a2a_server.py` | A2A protocol server factory | `specs/spec-S6.2-a2a-server/` | pending |
| S7.1 | Specialist Agents | `agents/valuation_scout.py` | Fundamentals agent | `specs/spec-S7.1-valuation-scout/` | pending |
| S7.2 | Specialist Agents | `agents/momentum_tracker.py` | Technical analysis agent | `specs/spec-S7.2-momentum-tracker/` | pending |
| S7.3 | Specialist Agents | `agents/pulse_monitor.py` | News sentiment agent | `specs/spec-S7.3-pulse-monitor/` | pending |
| S7.4 | Specialist Agents | `agents/economy_watcher.py` | Macro indicators agent | `specs/spec-S7.4-economy-watcher/` | pending |
| S7.5 | Specialist Agents | `agents/compliance_checker.py` | Regulatory risk agent | `specs/spec-S7.5-compliance-checker/` | pending |
| S7.6 | Specialist Agents | `agents/risk_guardian.py` | Portfolio risk agent | `specs/spec-S7.6-risk-guardian/` | pending |
| S8.1 | Orchestration | `agents/signal_synthesizer.py` | Signal fusion agent | `specs/spec-S8.1-signal-synthesizer/` | pending |
| S8.2 | Orchestration | `agents/market_conductor.py` | Orchestrator agent | `specs/spec-S8.2-market-conductor/` | pending |
| S8.3 | Orchestration | `agents/market_conductor.py` | Portfolio analysis | `specs/spec-S8.3-portfolio-analyzer/` | pending |
| S9.1 | API Layer | `app.py` | POST /analyze/{ticker} | `specs/spec-S9.1-analyze-endpoint/` | pending |
| S9.2 | API Layer | `app.py` | POST /portfolio | `specs/spec-S9.2-portfolio-endpoint/` | pending |
| S9.3 | API Layer | `app.py` | GET /history endpoints | `specs/spec-S9.3-history-endpoints/` | pending |
| S9.4 | API Layer | `app.py` | Error taxonomy | `specs/spec-S9.4-error-handling/` | pending |
| S10.1 | Pipeline Integration | `app.py` | Full pipeline wiring | `specs/spec-S10.1-pipeline-wiring/` | pending |
| S10.2 | Pipeline Integration | `agents/market_conductor.py` | Graceful degradation | `specs/spec-S10.2-graceful-degradation/` | pending |
| S10.3 | Pipeline Integration | `tests/test_pipeline.py` | Integration test | `specs/spec-S10.3-integration-test/` | pending |
| S11.1 | Infrastructure | `Dockerfile` | Multi-stage Dockerfile | `specs/spec-S11.1-dockerfile/` | pending |
| S11.2 | Infrastructure | `docker-compose.yml` | Local dev stack | `specs/spec-S11.2-docker-compose/` | pending |
| S11.3 | Infrastructure | `scripts/launch_agents.sh` | Launch/stop scripts | `specs/spec-S11.3-launch-scripts/` | pending |
| S11.4 | Infrastructure | `.dockerignore` | Docker ignore rules | `specs/spec-S11.4-dockerignore/` | pending |
| S11.5 | Infrastructure | `scripts/health_check.sh` | Health check script | `specs/spec-S11.5-health-check-script/` | pending |
| S12.1 | GCP Deployment | `.github/workflows/ci.yml` | CI pipeline | `specs/spec-S12.1-github-actions-ci/` | pending |
| S12.2 | GCP Deployment | `.github/workflows/deploy.yml` | CD pipeline | `specs/spec-S12.2-github-actions-cd/` | pending |
| S12.3 | GCP Deployment | `deploy/cloudrun.yaml` | Cloud Run config | `specs/spec-S12.3-cloud-run-config/` | pending |
| S12.4 | GCP Deployment | `deploy/setup-secrets.sh` | Secret Manager setup | `specs/spec-S12.4-secret-manager/` | pending |
| S12.5 | GCP Deployment | `deploy/setup-firestore.sh` | Firestore setup | `specs/spec-S12.5-firestore-setup/` | pending |
| S13.1 | Frontend | `frontend/` | Next.js scaffold | `specs/spec-S13.1-nextjs-scaffold/` | pending |
| S13.2 | Frontend | `frontend/app/page.tsx` | Analysis page | `specs/spec-S13.2-analysis-page/` | pending |
| S13.3 | Frontend | `frontend/app/components/` | Agent signal cards | `specs/spec-S13.3-agent-cards/` | pending |
| S13.4 | Frontend | `frontend/app/history/` | History view | `specs/spec-S13.4-history-view/` | pending |
| S14.1 | Evaluation & QA | `evaluation/quality_assessor.py` | Quality scoring | `specs/spec-S14.1-quality-assessor/` | pending |
| S14.2 | Evaluation & QA | `evaluation/benchmarks/` | Benchmark cases | `specs/spec-S14.2-benchmark-cases/` | pending |
| S14.3 | Evaluation & QA | `evaluation/backtester.py` | Backtesting | `specs/spec-S14.3-backtester/` | pending |
| S14.4 | Evaluation & QA | `tests/test_e2e.py` | E2E smoke test | `specs/spec-S14.4-e2e-smoke-test/` | pending |
| S14.5 | Evaluation & QA | `README.md`, `docs/` | Documentation | `specs/spec-S14.5-documentation/` | pending |
