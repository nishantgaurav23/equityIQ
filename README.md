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

## Quick Start

```bash
# Create virtual environment and install dependencies
make install-dev

# Copy environment template and add your API keys
cp .env.example .env

# Run tests
make local-test

# Run linter
make local-lint

# Start dev server
make local-dev
```

## Project Structure

```
equityiq/
├── config/              # Settings, data contracts, personas, logging
├── tools/               # API connectors (Polygon, FRED, NewsAPI, SEC)
├── models/              # XGBoost signal fusion, risk calculator
├── agents/              # ADK agent implementations
├── memory/              # SQLite/Firestore persistence
├── tests/               # Test suite (all externals mocked)
├── specs/               # Spec-driven development specs
├── app.py               # FastAPI entry point
├── pyproject.toml       # Dependencies and tool config
├── Makefile             # Developer commands
└── roadmap.md           # Full spec index and phase plan
```

## Development

This project follows **spec-driven, test-driven development**. The full build plan is in `roadmap.md` -- 14 phases, 55 specs covering foundation through deployment.

```bash
# Run tests
make local-test

# Lint and format check
make local-lint
```

## License

All rights reserved.
