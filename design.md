# Design -- EquityIQ: Multi-Agent Stock Intelligence System

## Architecture Overview

```
                        ┌──────────────────────┐
                        │   Next.js Frontend    │
                        │   (Dashboard + Chat)  │
                        └──────────┬───────────┘
                                   │ REST / WebSocket
                                   ▼
                        ┌──────────────────────┐
                        │   FastAPI Gateway     │
                        │   (app.py :8000)      │
                        │   /analyze/{ticker}   │
                        │   /portfolio          │
                        │   /chat               │
                        │   /health             │
                        └──────────┬───────────┘
                                   │ A2A Protocol (JSONRPC)
                                   ▼
                        ┌──────────────────────┐
                        │  Market Conductor     │
                        │  (Orchestrator :8000) │
                        │  asyncio.gather()     │
                        └──────────┬───────────┘
                                   │
              ┌────────┬───────┬───┴───┬────────┬────────┐
              ▼        ▼       ▼       ▼        ▼        ▼
         ┌────────┐ ┌──────┐ ┌─────┐ ┌──────┐ ┌──────┐ ┌──────┐
         │Valuation│ │Moment│ │Pulse│ │Econ  │ │Compli│ │Risk  │
         │Scout   │ │Tracker│ │Monit│ │Watch │ │Check │ │Guard │
         │:8001   │ │:8002 │ │:8003│ │:8004 │ │:8005 │ │:8007 │
         └───┬────┘ └──┬───┘ └──┬──┘ └──┬───┘ └──┬───┘ └──┬───┘
             │         │        │       │        │        │
             └────┬────┴────┬───┴───┬───┴────┬───┘        │
                  ▼         ▼       ▼        ▼            │
         ┌──────────────────────────────────────┐         │
         │       Signal Synthesizer (:8006)     │◀────────┘
         │       XGBoost Signal Fusion          │
         │       → STRONG_BUY/BUY/HOLD/SELL/    │
         │         STRONG_SELL                   │
         └──────────────────────────────────────┘

              ┌─────────────────────────────────┐
              │         Data Layer               │
              ├──────────┬──────────┬────────────┤
              │Polygon.io│ FRED API │ NewsAPI    │
              │(stocks)  │ (macro)  │ (sentiment)│
              ├──────────┼──────────┼────────────┤
              │SEC Edgar │ TTLCache │ SQLite /   │
              │(filings) │ (memory) │ Firestore  │
              └──────────┴──────────┴────────────┘
```

## User Flow -- Stock Analysis

1. User submits ticker via API or frontend: `POST /analyze/AAPL`
2. Market Conductor receives request, creates session ID (UUID)
3. Conductor dispatches to all 6 analyst agents in parallel via `asyncio.gather()`
4. Each agent:
   - Fetches data from its domain-specific API (via tools/)
   - Runs analysis using Gemini 3 Flash LLM with domain persona
   - Returns typed `AnalystReport` subclass with signal + confidence
5. Signal Synthesizer receives all 5 analyst reports:
   - Feeds features to XGBoost model for signal fusion
   - Applies compliance hard override (going_concern/restatement -> SELL)
   - Returns `FinalVerdict` with 5-level signal
6. Risk Guardian report attached separately (informs position sizing, not signal)
7. Response delivered to user with full breakdown + key drivers

### Edge Cases

- Agent timeout (>30s): Skip agent, reduce overall_confidence by 0.20
- API rate limit hit: Return cached data if available, fallback gracefully
- Compliance hard override: going_concern or restatement flags -> always SELL
- Low article count (<3): Cap confidence at 0.70
- All agents fail: Return error with "insufficient data" message

## Tech Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Agent Framework | Google ADK | Official Google agent kit, A2A protocol support |
| Agent Protocol | A2A v0.3.0 (JSONRPC) | Standard agent communication, discovery via agent cards |
| LLM | Gemini 3 Flash (`gemini-3-flash-preview`) | Fast, cost-effective for parallel agent calls |
| Backend | Python 3.12 / FastAPI / uvicorn | Async-native, strong ML ecosystem |
| ML Synthesis | XGBoost + scikit-learn | Signal fusion beyond weighted averaging |
| Validation | Pydantic v2 | Typed schemas for all agent I/O |
| Async HTTP | httpx + aiohttp | Non-blocking API calls to external services |
| Caching | cachetools.TTLCache | Rate limit protection (Polygon 5min, FRED 1hr) |
| Memory (local) | SQLite via aiosqlite | Zero-config local persistence |
| Memory (prod) | Firestore | Managed NoSQL, generous free tier |
| Frontend | Next.js + TypeScript + Tailwind | Modern dashboard with real-time updates |
| Deployment | Cloud Run (single container) | Auto-scaling 0-10, pay-per-use |
| CI/CD | GitHub Actions | Free for public repos, 2000 min/month private |
| Secrets | GCP Secret Manager | Free tier (6 active versions) |
| Config | pydantic-settings + .env | All secrets via environment, no hardcoded keys |
| Testing | pytest + pytest-asyncio | Async test suite, all external services mocked |
| Linting | ruff (line-length: 100) | Fast, opinionated formatting |

## Data Flow

```
Request: POST /analyze/AAPL
         │
         ▼
┌──────────────────────────────────┐
│ 1. Market Conductor receives     │
│    request, creates session_id   │
│    (UUID), validates ticker      │
└──────────────┬───────────────────┘
               │ asyncio.gather()
               ▼
┌──────────────────────────────────┐
│ 2. All 6 agents run in parallel: │
│    - ValuationScout → Polygon    │
│    - MomentumTracker → Polygon   │
│      + technical_engine          │
│    - PulseMonitor → NewsAPI      │
│      + Polygon news              │
│    - EconomyWatcher → FRED       │
│    - ComplianceChecker → SEC     │
│    - RiskGuardian → Polygon      │
└──────────────┬───────────────────┘
               │ 5 AnalystReports + RiskGuardianReport
               ▼
┌──────────────────────────────────┐
│ 3. Signal Synthesizer:           │
│    - Extract features from       │
│      all reports                 │
│    - Feed to XGBoost model       │
│    - Apply compliance override   │
│    - Apply confidence thresholds │
│    - Generate FinalVerdict       │
└──────────────┬───────────────────┘
               │
               ▼
┌──────────────────────────────────┐
│ 4. Store verdict in InsightVault │
│    (SQLite local / Firestore     │
│    production). Return to user.  │
└──────────────────────────────────┘
```

## Signal Weighting (XGBoost Features)

Default weights for fallback weighted-average mode:
- ValuationScout: 0.25
- MomentumTracker: 0.20
- PulseMonitor: 0.20
- EconomyWatcher: 0.20
- ComplianceChecker: 0.15

Dynamic adjustments:
- Contraction/stagflation regime -> EconomyWatcher weight -> 0.30
- Earnings season -> PulseMonitor weight -> 0.30

## Hard Rules (Safety Design)

| Risk | Mitigation |
|------|-----------|
| False BUY on regulatory red flag | ComplianceChecker going_concern or restatement -> always SELL override regardless of other signals |
| Overconfident on thin data | Never assign confidence > 0.70 on fewer than 3 news articles |
| Extreme signals without justification | STRONG_BUY/STRONG_SELL requires overall_confidence >= 0.75 |
| Over-concentration risk | RiskGuardian: suggested_position_size never > 0.10 (10% max per stock) |
| API failure cascading | Each agent wrapped in try/except; missing agent reduces confidence by 0.20 |
| Rate limit breach | TTLCache on all API calls (Polygon 5min, FRED 1hr) |

## GCP Deployment Architecture (Under $50/month)

```
GitHub (main branch)
    │
    ▼ (push trigger)
GitHub Actions CI/CD
    │
    ├── Run tests (pytest)
    ├── Run lint (ruff)
    ├── Build Docker image
    ├── Push to Artifact Registry
    └── Deploy to Cloud Run
              │
              ▼
┌──────────────────────────────────┐
│ Cloud Run (single container)     │
│ - All 7 agents as internal       │
│   async functions (not separate  │
│   services)                      │
│ - FastAPI gateway on port 8080   │
│ - Auto-scale: 0-4 instances      │
│ - Memory: 1GB, CPU: 1            │
│ - Min instances: 0 (scale to 0)  │
└──────────────┬───────────────────┘
               │
    ┌──────────┼──────────┐
    ▼          ▼          ▼
Firestore   Secret     Cloud
(verdicts)  Manager    Logging
(free tier) (free)     (50GB free)
```

### GCP Cost Estimate

| Resource | Tier | Est. Monthly Cost |
|----------|------|-------------------|
| Cloud Run (1 container, 0-4 instances) | Free tier: 2M requests, 360K GB-s | $0-5 |
| Artifact Registry | 500MB free | $0 |
| Firestore | Free tier: 1GB, 50K reads/day | $0 |
| Secret Manager | 6 active versions free | $0 |
| Cloud Logging | 50GB/month free | $0 |
| Gemini API | Pay-per-call (~$0.01/analysis) | $5-15 |
| Polygon.io | Free tier (5 req/min) | $0 |
| FRED API | Free | $0 |
| NewsAPI | Free tier (100 req/day) | $0 |
| **Total (prototype volume)** | | **$5-20/month** |

Budget buffer of $30-45 available for overages or scaling up Cloud Run instances.

### Production Deployment Strategy

For production under $50/month, use a **monolith-in-a-container** approach:
- All 7 agents run as async Python functions inside a single FastAPI app
- No inter-service HTTP calls -- direct function invocation
- A2A protocol endpoints still exposed for external agent discovery
- Single Cloud Run container with 1GB memory handles everything
- Scale to 0 when idle, auto-scale to 4 on demand

This avoids the cost of 8 separate Cloud Run services while maintaining the agent architecture internally.

## Security Design

| Concern | Approach |
|---------|----------|
| API key storage | GCP Secret Manager (prod), .env file (local). Never in code or git |
| Input validation | Pydantic v2 validates all inputs at API boundary |
| Rate limiting | TTLCache prevents API abuse; Cloud Run concurrency limits |
| HTTPS | Cloud Run provides Google-managed TLS certificates |
| CORS | Restrict to frontend domain only |
| Dependency security | Dependabot alerts via GitHub, pin major versions |
| Container security | Non-root user in Dockerfile, minimal base image |
| Logging | Structured logs via Cloud Logging, no sensitive data in logs |
