# 01 — Project Overview

  ## What Problem Are We Solving?

  Stock market analysis requires looking at many independent dimensions at the same time:
  - Is the company financially healthy? (fundamentals)
  - Is the price trending up or down? (technicals)
  - What is the market saying about it? (sentiment)
  - What is the broder economy doing? (macro)
  - Are there any leagal or regulatory risks? (compliance)
  - How risky is holidng this position? (portfolio risk)

A single analyst - human or AI - cannot go deep on all six simulataneously.
EquityIQ assigns one specialist agent to each dimentsion, runs them all in parallel,
and fuses their signals into a single actionable recommendation.

---

## Why this Approach?

### Domain Depth
Each agent has a focused system prompt, focused tools, and focused data.
The Valuation Scout only thinks about financials. The Momentum Tracker only
thinks abouts price action. Specialists go deeper than generalists.

### Speed Through Parallelism
All 7 agents run at thhe same time using `asyncio.gether()`.
Total analysis time ≈ time of the slowest single agent, not the sum of all.

### Transparency
Every agent's signal is viisble. You can see exactly which agent pushed
the recommendation in which direction and why.

### Graceful Degradation
If one agent fails (e.g., NewsAPI is down), the other 6 continue.
The system reduces overall confidence but still delivers a result. 

## The 7 Agents at a Glance

| Agent | File | Port | Question It Answers |
|---|---|---|---|
| Valuation Scout | `valuation_scout.py` | 8001 | Is this company financially sound and fairly priced? |
| Momentum Tracker | `momentum_tracker.py` | 8002 | What is the price trend and momentum saying? |
| Pulse Monitor | `pulse_monitor.py` | 8003 | What is the market narrative around this stock? |
| Economy Watcher | `economy_watcher.py` | 8004 | Is the macro environment supportive or hostile? |
| Compliance Checker | `compliance_checker.py` | 8005 | Are there any regulatory or legal red flags? |
| Signal Synthesizer | `signal_synthesizer.py` | 8006 | What does the combined picture say? |
| Risk Guardian | `risk_guardian.py` | 8007 | How much risk am I taking on with this position? |

---

## System Architecture

User Request (ticker + horizon)
        │
        ▼
market_conductor.py          ← Orchestrator: coordinates everything
        │
        │  asyncio.gather() — all 5 analysts run simultaneously
        ├──────────────────────────────────────────────┐
        │                    │              │           │           │
        ▼                    ▼              ▼           ▼           ▼
valuation_scout          momentum_tracker  pulse_monitor  economy_watcher  compliance_checker
(Port 8001)             (Port 8002)     (Port 8003)   (Port 8004)      (Port 8005)
Polygon.io              Polygon.io      NewsAPI        FRED API         SEC Edgar
        │                    │              │           │           │
        └──────────────────────────────────────────────┘
                            │
                            ▼
                    signal_synthesizer        ← Fuses all 5 signals
                        (Port 8006)
                            │
                            ▼
                    risk_guardian            ← Assesses position risk
                        (Port 8007)
                            │
                            ▼
                        insight_vault           ← Persists result to SQLite
                            │
                            ▼
                    Final Report to User

---

## What Is Built In From Day One

These are not future work — they are part of the initial build:

| Capability | Where |
|---|---|
| Persistent analysis history | `memory/insight_vault.py` |
| Agent quality testing | `evaluation/quality_assessor.py` |
| Historical accuracy testing | `evaluation/backtester.py` |
| Portfolio-level analysis | `agents/market_conductor.py` |
| ML-based signal fusion | `models/signal_fusion.py` |
| Dedicated risk agent | `agents/risk_guardian.py` |
| Natural language endpoint | `POST /chat` in `app.py` |
| API response caching | TTL cache in every `tools/*.py` |
| Vertex AI deployment | `deploy/vertex-deploy.sh` |

---

## Data Sources

| Source | What It Provides | Cost |
|---|---|---|
| Polygon.io | Price, fundamentals, technicals, news | Free tier: 5 calls/min |
| FRED API | GDP, inflation, Fed rate, unemployment | Free, no rate limit |
| NewsAPI | News headlines and articles | Free: 100 calls/day |
| SEC Edgar | 10-K, 10-Q, 8-K filings | Free, public |
| Yahoo Finance (yfinance) | Fallback for price data | Free |

---

## Build Order

Always build in this sequence — each layer depends on the one before it.

Layer 1 — Contracts    : config/data_contracts.py
Layer 2 — Personas     : config/analyst_personas.py
Layer 3 — Data Feeds   : tools/.py
Layer 4 — ML Models    : models/signal_fusion.py
Layer 5 — Memory       : memory/insight_vault.py
Layer 6 — Agents       : agents/.py  (one at a time)
Layer 7 — Orchestrator : agents/market_conductor.py
Layer 8 — Entry Point  : app.py
Layer 9 — Ops          : scripts/.sh
Layer 10 — Evaluation  : evaluation/.py