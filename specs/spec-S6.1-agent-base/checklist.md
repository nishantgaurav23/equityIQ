# Checklist S6.1 -- ADK Agent Base Class

## File: `agents/base_agent.py`

- [x] Create `agents/` package with `__init__.py`
- [x] Implement `BaseAnalystAgent.__init__()` -- accepts agent_name, output_schema, tools, model
- [x] Validate agent_name against PERSONAS dict (KeyError if missing)
- [x] Create underlying ADK `Agent` with correct name, model, instruction, tools, output_schema
- [x] Implement `.agent` property returning ADK Agent instance
- [x] Implement `.name` property
- [x] Implement `.persona` property
- [x] Implement `analyze(ticker)` -- create Runner, session, send message, parse response
- [x] Error handling in `analyze()` -- never raises, returns HOLD/0.0 fallback on failure
- [x] Implement `get_agent_card()` -- returns A2A discovery dict
- [x] Agent card URL resolution from Settings
- [x] Implement `create_agent()` module-level factory function

## Tests: `tests/test_base_agent.py`

- [x] test_init_with_valid_persona
- [x] test_init_with_invalid_persona
- [x] test_init_default_model
- [x] test_init_custom_model
- [x] test_init_with_tools
- [x] test_init_no_tools
- [x] test_adk_agent_created
- [x] test_adk_agent_has_correct_instruction
- [x] test_adk_agent_has_correct_output_schema
- [x] test_analyze_success
- [x] test_analyze_returns_correct_schema
- [x] test_analyze_error_returns_fallback
- [x] test_analyze_fallback_has_error_message
- [x] test_analyze_never_raises
- [x] test_get_agent_card_structure
- [x] test_get_agent_card_url_from_settings
- [x] test_get_agent_card_capabilities
- [x] test_create_agent_factory
- [x] test_all_personas_can_create_agent

## Quality

- [x] `ruff check agents/` passes
- [x] `ruff format agents/` passes
- [x] All tests pass: `python -m pytest tests/test_base_agent.py -v` (23 passed)
- [x] No hardcoded API keys
- [x] All external calls wrapped in try/except
