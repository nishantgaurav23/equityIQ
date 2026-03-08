# Checklist S6.2 -- A2A Protocol Server Factory

## File: `agents/a2a_server.py`

- [x] A2ATextPart model
- [x] A2AMessage model
- [x] A2ATaskParams model
- [x] A2ARequest model
- [x] create_agent_server() factory function
- [x] GET /.well-known/agent-card.json endpoint
- [x] POST /a2a JSONRPC handler
- [x] tasks/send method handling
- [x] JSONRPC error responses (-32600, -32601, -32602)
- [x] GET /health endpoint
- [x] Ticker extraction from message parts

## Tests: `tests/test_a2a_server.py`

- [x] test_agent_card_endpoint
- [x] test_agent_card_has_required_fields
- [x] test_health_endpoint
- [x] test_a2a_tasks_send_success
- [x] test_a2a_tasks_send_result_structure
- [x] test_a2a_tasks_send_artifact_contains_report
- [x] test_a2a_tasks_send_preserves_task_id
- [x] test_a2a_unknown_method
- [x] test_a2a_invalid_request_body
- [x] test_a2a_missing_params
- [x] test_a2a_missing_text_in_parts
- [x] test_a2a_agent_fallback_still_completes
- [x] test_create_agent_server_returns_fastapi
- [x] test_server_reusable_with_different_agents

## Quality Gates

- [x] ruff check passes
- [x] All tests pass (16/16)
- [x] roadmap.md status updated to done
