# Checklist S7.3 -- PulseMonitor Agent

## Implementation Checklist

### T1: Module Setup
- [x] Create `agents/pulse_monitor.py`
- [x] Import BaseAnalystAgent, PulseReport, NewsConnector, PolygonConnector
- [x] Module-level `_news_connector` and `_polygon_connector` instances
- [x] Logger setup

### T2: Tool Functions
- [x] `get_news_sentiment_tool(ticker)` wraps NewsConnector.get_news_sentiment()
- [x] `get_company_news_tool(ticker)` wraps PolygonConnector.get_company_news()
- [x] Both return `{}` on error
- [x] Both log warnings on error
- [x] Both never raise exceptions

### T3: Agent Class
- [x] `PulseMonitorAgent` extends `BaseAnalystAgent`
- [x] agent_name = "pulse_monitor"
- [x] output_schema = PulseReport
- [x] tools = [get_news_sentiment_tool, get_company_news_tool]
- [x] Inherits analyze() from base

### T4: Module Exports
- [x] Module-level `pulse_monitor` instance
- [x] Factory function `create_pulse_monitor()`

### T5: Error Handling
- [x] Tool errors return `{}`
- [x] analyze() fallback returns HOLD/0.0
- [x] No exceptions propagate

### T6: Tests
- [x] Test file: `tests/test_pulse_monitor.py`
- [x] Test tool functions (success, error, exception cases)
- [x] Test agent instantiation and properties
- [x] Test agent card structure
- [x] Test analyze success (mocked LLM)
- [x] Test analyze fallback (mocked error)
- [x] Test confidence cap (<3 articles -> max 0.70)
- [x] All 23 tests pass
- [x] ruff clean

### T7: Verification
- [x] `ruff check agents/pulse_monitor.py` passes
- [x] `ruff check tests/test_pulse_monitor.py` passes
- [x] All tests pass: `python -m pytest tests/test_pulse_monitor.py -v`

## Status: done
