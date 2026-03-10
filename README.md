# EquityIQ

Multi-agent stock intelligence system. 7 specialist AI agents analyze stocks in parallel, and an XGBoost synthesizer fuses their signals into a final BUY/HOLD/SELL verdict.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                 MarketConductor (8000)               │
│              Orchestrator -- routes & aggregates     │
├──────────┬──────────┬──────────┬──────────┬─────────┤
│Valuation │Momentum  │ Pulse    │ Economy  │Compliance│
│Scout     │Tracker   │ Monitor  │ Watcher  │Checker   │
│  8001    │  8002    │  8003    │  8004    │  8005    │
├──────────┴──────────┴──────────┴──────────┴─────────┤
│              SignalSynthesizer (8006)                 │
│         XGBoost fusion -> final verdict              │
├─────────────────────────────────────────────────────┤
│              RiskGuardian (8007)                      │
│         Beta, volatility, position sizing            │
└─────────────────────────────────────────────────────┘
```

Each agent produces a typed `AnalystReport` (Pydantic v2). The synthesizer fuses all signals using an XGBoost model (with weighted-average fallback) into a 5-level verdict: STRONG_BUY / BUY / HOLD / SELL / STRONG_SELL.

For detailed architecture docs, see [docs/architecture.md](docs/architecture.md).

## Tech Stack

| Layer | Technology |
|-------|------------|
| Agent Framework | Google ADK + A2A v0.3.0 |
| LLM | Gemini 3 Flash |
| Backend | Python 3.12 / FastAPI / uvicorn |
| ML Synthesis | XGBoost + scikit-learn |
| Validation | Pydantic v2 + pydantic-settings |
| Caching | cachetools (TTLCache) |
| Memory | SQLite (local) / Firestore (prod) |
| Frontend | Next.js + TypeScript + Tailwind |
| Deployment | GCP Cloud Run (single container) |
| CI/CD | GitHub Actions |

## Data Sources

- **Polygon.io** -- fundamentals, price history, company news
- **FRED** -- macro indicators (GDP, inflation, fed funds rate)
- **NewsAPI** -- news sentiment and event detection
- **SEC Edgar** -- filings, regulatory risk scoring
- **Yahoo Finance** -- global price data, Indian market support

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 18+ (for frontend)
- API keys: Google AI, Polygon.io, FRED, NewsAPI (see [Environment Variables](#environment-variables))

### Setup

```bash
# Clone the repository
git clone https://github.com/nishantgaurav23/equityiq.git
cd equityiq

# Create virtual environment and install dependencies
make install-dev

# Copy environment template and add your API keys
cp .env.example .env
# Edit .env with your API keys

# Run tests to verify setup
make local-test

# Start the development server
make local-dev
```

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The frontend runs at `http://localhost:3000`.

## Running Tests

```bash
# Run full test suite
make local-test

# Or directly with pytest
source venv/bin/activate
python -m pytest tests/ -v --tb=short

# Run a specific test file
python -m pytest tests/test_pipeline.py -v

# Run linter
make local-lint
```

All external services (Polygon, FRED, NewsAPI, SEC Edgar, Gemini) are mocked in tests. No API keys needed to run the test suite.

### Test Structure

```
tests/
├── test_settings.py           # Config and settings
├── test_polygon_connector.py  # Polygon.io connector
├── test_fred_connector.py     # FRED API connector
├── test_base_agent.py         # Base agent framework
├── test_valuation_scout.py    # Valuation agent
├── test_momentum_tracker.py   # Momentum agent
├── test_pulse_monitor.py      # Pulse/sentiment agent
├── test_economy_watcher.py    # Economy agent
├── test_compliance_checker.py # Compliance agent
├── test_risk_guardian.py      # Risk agent
├── test_signal_synthesizer.py # Signal fusion
├── test_market_conductor.py   # Orchestrator
├── test_pipeline.py           # Integration tests
├── test_api_routes.py         # API endpoint tests
├── test_e2e.py                # End-to-end smoke test
└── ...
```

## Docker

```bash
# Start dev container with hot-reload
make dev

# Run tests in container
make test

# Build production image
docker build --target prod -t equityiq:prod .
```

See [docs/deployment.md](docs/deployment.md) for full deployment instructions.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/analyze/{ticker}` | Full multi-agent analysis |
| POST | `/api/v1/portfolio` | Portfolio analysis (up to 10 tickers) |
| GET | `/api/v1/history/{ticker}` | Past verdicts for a ticker |
| GET | `/api/v1/history` | Recent verdicts across all tickers |
| GET | `/api/v1/search?q=...` | Ticker search |
| GET | `/api/v1/price-history/{ticker}` | OHLCV price data |
| GET | `/health` | Health check |

Full API reference: [docs/api-reference.md](docs/api-reference.md)

## Environment Variables

Create a `.env` file from the template:

```bash
cp .env.example .env
```

| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_API_KEY` | Yes | Google AI / Gemini API key |
| `POLYGON_API_KEY` | Yes | Polygon.io API key |
| `FRED_API_KEY` | Yes | FRED API key |
| `NEWS_API_KEY` | Yes | NewsAPI key |
| `ENVIRONMENT` | No | `local` (default) or `production` |
| `SQLITE_DB_PATH` | No | SQLite path (default: `data/equityiq.db`) |
| `LOG_LEVEL` | No | DEBUG, INFO (default), WARNING, ERROR |
| `GCP_PROJECT_ID` | No | GCP project ID (production only) |
| `GCP_REGION` | No | GCP region (default: `us-central1`) |

## Project Structure

```
equityiq/
├── config/              # Settings, data contracts, personas, logging
├── tools/               # API connectors (Polygon, FRED, NewsAPI, SEC, Yahoo)
├── models/              # XGBoost signal fusion, risk calculator
├── agents/              # ADK agent implementations (7 + conductor)
├── memory/              # SQLite/Firestore persistence
├── api/                 # FastAPI routes, error handling, chat
├── evaluation/          # Quality assessor, benchmarks, backtester
├── frontend/            # Next.js + TypeScript dashboard
├── tests/               # Test suite (all externals mocked)
├── scripts/             # Launch, stop, health check scripts
├── specs/               # Spec-driven development specs
├── docs/                # API reference, architecture, deployment
├── app.py               # FastAPI entry point
├── pyproject.toml       # Dependencies and tool config
├── Makefile             # Developer commands
├── Dockerfile           # Multi-stage build
├── docker-compose.yml   # Local dev container
└── roadmap.md           # Full spec index and phase plan
```

## Development

This project follows **spec-driven, test-driven development**. The full build plan is in `roadmap.md` -- 17 phases, 62 specs covering foundation through integrations.

### Make Commands

| Command | Description |
|---------|-------------|
| `make venv` | Create virtual environment |
| `make install` | Install runtime dependencies |
| `make install-dev` | Install runtime + dev dependencies |
| `make local-dev` | Start dev server with hot-reload |
| `make local-test` | Run test suite |
| `make local-lint` | Run ruff linter and formatter |
| `make dev` | Start Docker dev container |
| `make test` | Run tests in Docker |

## License

All rights reserved.
