# S15.2 -- Rich Analysis Response -- Checklist

## Status: done

## TDD Checklist

- [x] **Write tests** (`tests/test_rich_analysis_response.py`)
  - [x] Test FinalVerdict.analyst_details has per-agent entries
  - [x] Test each detail has signal, confidence, reasoning, key_metrics, data_source, execution_time_ms
  - [x] Test risk_level HIGH when signal std > 0.6
  - [x] Test risk_level HIGH when avg confidence < 0.40
  - [x] Test risk_level MEDIUM when signal std > 0.3
  - [x] Test risk_level MEDIUM when avg confidence < 0.60
  - [x] Test risk_level LOW for agreeing high-confidence signals
  - [x] Test execution_time_ms is populated and > 0
  - [x] Test backward compatibility -- analyst_signals dict still present
- [x] **Implement schema** (`config/data_contracts.py`)
  - [x] Create `AgentDetail` Pydantic model (signal, confidence, reasoning, key_metrics, data_source, execution_time_ms)
  - [x] Add `analyst_details: dict[str, AgentDetail]` to FinalVerdict
  - [x] Add `risk_level: str` to FinalVerdict (default "MEDIUM")
  - [x] Add `execution_time_ms: int` to FinalVerdict
  - [x] Keep `analyst_signals` for backward compatibility
- [x] **Implement risk calculation** (`agents/market_conductor.py`)
  - [x] Calculate signal std from agent numeric signals
  - [x] Calculate avg confidence from agent reports
  - [x] Apply risk level thresholds (HIGH/MEDIUM/LOW)
  - [x] Populate analyst_details from agent reports
  - [x] Track total execution time with time.perf_counter()
- [x] **Verify**
  - [x] All tests pass: `python -m pytest tests/test_rich_analysis_response.py -v`
  - [x] Ruff clean: `ruff check config/data_contracts.py agents/market_conductor.py`
  - [x] Existing FinalVerdict tests still pass
