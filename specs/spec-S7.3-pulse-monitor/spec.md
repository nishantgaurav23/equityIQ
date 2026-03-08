# Spec S7.3 -- PulseMonitor Agent

## Overview
PulseMonitor is a news sentiment analyst agent that aggregates news sentiment, detects market-moving events, and returns a PulseReport with BUY/HOLD/SELL signal. It extends BaseAnalystAgent (S6.1) and uses NewsConnector (S3.3) + PolygonConnector (S3.1) for data.

**Port**: 8003
**Output**: `PulseReport`
**Dependencies**: S6.1 (BaseAnalystAgent), S3.3 (NewsConnector), S3.1 (PolygonConnector)

---

## Architecture

```
PulseMonitor (BaseAnalystAgent)
  ├── get_news_sentiment_tool(ticker)  -> news sentiment dict
  ├── get_company_news_tool(ticker)    -> polygon company news dict
  └── analyze(ticker) -> PulseReport
```

### Data Flow
1. Gemini calls `get_news_sentiment_tool(ticker)` to get sentiment_score, article_count, top_headlines, event_flags from NewsConnector
2. Gemini calls `get_company_news_tool(ticker)` to get additional headlines from PolygonConnector
3. LLM synthesizes both data sources into a PulseReport with signal, confidence, reasoning

---

## Tool Functions

### `get_news_sentiment_tool(ticker: str) -> dict`
- Wraps `NewsConnector.get_news_sentiment(ticker)`
- Returns dict with: `sentiment_score`, `article_count`, `top_headlines`, `event_flags`
- On error: returns `{}`, logs warning
- Never raises exceptions

### `get_company_news_tool(ticker: str) -> dict`
- Wraps `PolygonConnector.get_company_news(ticker)`
- Returns dict with: `headlines`, `articles`
- On error: returns `{}`, logs warning
- Never raises exceptions

---

## Agent Class

### `PulseMonitorAgent(BaseAnalystAgent)`
- `agent_name`: `"pulse_monitor"`
- `output_schema`: `PulseReport`
- `tools`: `[get_news_sentiment_tool, get_company_news_tool]`
- Inherits `analyze(ticker)` and `get_agent_card()` from BaseAnalystAgent

### Signal Logic (enforced by LLM persona)
- **BUY**: Strong positive sentiment (>0.3) + bullish events (earnings beat, upgrade, FDA approval)
- **SELL**: Strong negative sentiment (<-0.3) + bearish events (earnings miss, downgrade, lawsuit)
- **HOLD**: Neutral sentiment, no significant events

### Critical Rules
1. **Confidence cap**: NEVER assign confidence > 0.70 when `article_count < 3` (enforced by PulseReport model_validator)
2. **Sentiment clamping**: sentiment_score always in [-1.0, 1.0] (enforced by PulseReport field_validator)
3. **Top headlines**: Up to 5 headlines in top_headlines list
4. **Event detection**: All detected events listed in event_flags

---

## Module-Level Exports

```python
_news_connector = NewsConnector()
_polygon_connector = PolygonConnector()

pulse_monitor = PulseMonitorAgent()  # or via create_pulse_monitor() factory
```

---

## Error Handling

- Tool function exceptions: caught, logged, return `{}`
- Agent analyze failure: BaseAnalystAgent._fallback_report() returns HOLD/0.0
- No exception ever propagates to caller

---

## File Locations

| Artifact | Path |
|----------|------|
| Agent | `agents/pulse_monitor.py` |
| Tests | `tests/test_pulse_monitor.py` |
| Persona | `config/analyst_personas.py` (key: `pulse_monitor`) |
| Schema | `config/data_contracts.py` (class: `PulseReport`) |

---

## Tangible Outcomes

1. `agents/pulse_monitor.py` exists with PulseMonitorAgent class
2. Two tool functions: `get_news_sentiment_tool`, `get_company_news_tool`
3. All tests in `tests/test_pulse_monitor.py` pass
4. `ruff check agents/pulse_monitor.py` clean
5. Agent card returned by `get_agent_card()` has correct structure
6. Fallback to HOLD/0.0 on any error
7. Confidence capped at 0.70 when <3 articles (via PulseReport validator)
