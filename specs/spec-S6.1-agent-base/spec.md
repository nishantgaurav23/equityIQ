# Spec S6.1 -- ADK Agent Base Class

## Overview

Base class that wraps Google ADK `Agent` for EquityIQ specialist agents. Provides a consistent pattern for creating agents with personas, tools, typed output schemas, error handling, and A2A agent card generation.

## Location

`agents/base_agent.py`

## Dependencies

| Spec | What it provides |
|------|-----------------|
| S1.3 | `config/settings.py` -- Settings, get_settings() |
| S2.1 | `config/data_contracts.py` -- AnalystReport and all subclass schemas |
| S2.3 | `config/analyst_personas.py` -- PERSONAS dict with system prompts |

## Public API

### `BaseAnalystAgent`

A wrapper class that creates and configures a Google ADK `Agent` instance with EquityIQ conventions.

```python
class BaseAnalystAgent:
    """Base class for all EquityIQ analyst agents."""

    def __init__(
        self,
        agent_name: str,                          # key in PERSONAS dict
        output_schema: type[AnalystReport],        # Pydantic model for typed output
        tools: list[Callable] | None = None,       # tool functions the agent can call
        model: str = "gemini-3-flash-preview",     # LLM model ID
    ) -> None: ...

    @property
    def agent(self) -> Agent:
        """Returns the underlying ADK Agent instance."""

    @property
    def name(self) -> str:
        """Agent name."""

    @property
    def persona(self) -> str:
        """System prompt from PERSONAS dict."""

    async def analyze(self, ticker: str) -> AnalystReport:
        """
        Run analysis for the given ticker.

        Creates an ADK Runner + InMemorySessionService, sends the ticker
        as a user message, and returns the parsed output_schema instance.

        On any error (LLM failure, parsing error, timeout), returns a
        fallback AnalystReport with signal=HOLD, confidence=0.0, and
        the error in reasoning.
        """

    def get_agent_card(self) -> dict:
        """
        Generate an A2A-compatible agent card for discovery.

        Returns dict with:
        - name: agent display name
        - description: first line of persona
        - url: agent URL from settings
        - capabilities: list of tool names
        - output_schema: schema name
        """
```

### `create_agent(agent_name, output_schema, tools, model)` (module-level)

Convenience factory function that returns a `BaseAnalystAgent` instance.

## Implementation Details

### ADK Agent Configuration

The underlying `google.adk.agents.Agent` is created with:
- `name`: `agent_name` parameter
- `model`: model parameter (default `"gemini-3-flash-preview"`)
- `instruction`: persona string from `PERSONAS[agent_name]`
- `tools`: tool functions list (empty list if None)
- `output_schema`: Pydantic model class for typed output

### analyze() Flow

1. Create `InMemorySessionService` and a new session
2. Create `Runner` with the ADK agent and session service
3. Send user message: `f"Analyze stock ticker: {ticker}"`
4. Iterate through runner events, collect the final agent response
5. Parse the response into `output_schema` instance
6. Return the typed report

### Error Handling

- All external calls (LLM, tool execution) are wrapped in try/except
- On failure, return a fallback report:
  - `ticker`: the requested ticker
  - `agent_name`: this agent's name
  - `signal`: "HOLD" (safe default)
  - `confidence`: 0.0 (no confidence in fallback)
  - `reasoning`: f"Analysis failed: {error_message}"
- Never raise exceptions from `analyze()` -- agents must not crash

### Agent Card Format

```json
{
  "name": "valuation_scout",
  "description": "Senior equity research analyst specializing in fundamental stock valuation.",
  "url": "http://localhost:8001",
  "capabilities": ["get_fundamentals"],
  "output_schema": "ValuationReport"
}
```

Agent URLs are resolved from `Settings` using a mapping:
- `valuation_scout` -> `VALUATION_AGENT_URL`
- `momentum_tracker` -> `MOMENTUM_AGENT_URL`
- `pulse_monitor` -> `PULSE_AGENT_URL`
- `economy_watcher` -> `ECONOMY_AGENT_URL`
- `compliance_checker` -> `COMPLIANCE_AGENT_URL`
- `signal_synthesizer` -> `SYNTHESIZER_AGENT_URL`
- `risk_guardian` -> `RISK_AGENT_URL`

## Tangible Outcomes

1. `agents/base_agent.py` exists with `BaseAnalystAgent` class and `create_agent()` factory
2. All tests pass: `python -m pytest tests/test_base_agent.py -v`
3. `ruff check agents/` passes with no errors
4. Can instantiate a BaseAnalystAgent with any persona from PERSONAS dict
5. `analyze()` returns a typed AnalystReport subclass on success
6. `analyze()` returns a safe fallback (HOLD, 0.0 confidence) on failure -- never raises
7. `get_agent_card()` returns valid A2A discovery dict
8. Agent card URLs match Settings values

## Test Plan

### Unit Tests (`tests/test_base_agent.py`)

1. **test_init_with_valid_persona** -- create agent with "valuation_scout", verify name, persona, output_schema
2. **test_init_with_invalid_persona** -- unknown agent_name raises KeyError
3. **test_init_default_model** -- default model is "gemini-3-flash-preview"
4. **test_init_custom_model** -- can override model
5. **test_init_with_tools** -- tools list is passed to ADK Agent
6. **test_init_no_tools** -- tools defaults to empty list
7. **test_adk_agent_created** -- `.agent` property returns ADK Agent instance
8. **test_adk_agent_has_correct_instruction** -- instruction matches PERSONAS[name]
9. **test_adk_agent_has_correct_output_schema** -- output_schema set on ADK Agent
10. **test_analyze_success** -- mock Runner to return valid response, verify typed report
11. **test_analyze_returns_correct_schema** -- ValuationReport for valuation agent
12. **test_analyze_error_returns_fallback** -- mock Runner to raise, get HOLD/0.0 fallback
13. **test_analyze_fallback_has_error_message** -- reasoning contains error info
14. **test_analyze_never_raises** -- even on unexpected errors, returns fallback
15. **test_get_agent_card_structure** -- has name, description, url, capabilities, output_schema
16. **test_get_agent_card_url_from_settings** -- URL matches Settings field
17. **test_get_agent_card_capabilities** -- lists tool function names
18. **test_create_agent_factory** -- module-level factory returns BaseAnalystAgent
19. **test_all_personas_can_create_agent** -- iterate PERSONAS, create agent for each

All ADK/LLM calls must be mocked -- no real Gemini calls in tests.
