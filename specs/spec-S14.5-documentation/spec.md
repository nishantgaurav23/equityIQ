# Spec S14.5 -- Final Documentation

## Overview
Comprehensive project documentation covering local setup, running tests, deployment guide, API reference, and architecture overview. Ensures any developer can onboard quickly and understand the system.

## Dependencies
- S10.3 (Integration Test) -- full pipeline must be tested and working

## Target Location
- `README.md` (main project README)
- `docs/` (additional documentation)
- `tests/test_documentation.py` (validation tests)

---

## Functional Requirements

### FR-1: README with Local Setup Guide
- **What**: `README.md` includes complete local development setup instructions
- **Inputs**: Fresh clone of the repository
- **Outputs**: Developer can set up and run the project following only the README
- **Must include**: Prerequisites (Python 3.12, Node.js 18+), venv creation, dependency installation, environment variable setup (.env.example reference), running the backend, running the frontend
- **Edge cases**: Both macOS and Linux instructions where they differ

### FR-2: Testing Documentation
- **What**: README includes how to run the full test suite
- **Inputs**: Developer with local setup complete
- **Outputs**: Clear commands for running tests, linting, and checking coverage
- **Must include**: `make local-test`, `make local-lint`, pytest direct commands, test structure explanation

### FR-3: API Reference
- **What**: `docs/api-reference.md` documents all REST API endpoints
- **Inputs**: All endpoints from `api/routes.py`
- **Outputs**: Complete API docs with request/response examples
- **Must include**: POST /api/v1/analyze/{ticker}, POST /api/v1/portfolio, GET /api/v1/history, GET /api/v1/search/tickers, GET /health
- **Each endpoint**: Method, URL, request body (if any), response schema, example curl, status codes

### FR-4: Architecture Overview
- **What**: `docs/architecture.md` explains the multi-agent system design
- **Inputs**: System design from design.md and CLAUDE.md
- **Outputs**: Clear architecture documentation with agent descriptions, data flow, signal fusion
- **Must include**: Agent table (7 agents + conductor), data flow (request -> agents -> synthesizer -> verdict), signal weighting, key design decisions (parallel execution, XGBoost synthesis, compliance override, graceful degradation)

### FR-5: Deployment Guide
- **What**: `docs/deployment.md` covers Docker local and GCP Cloud Run deployment
- **Inputs**: Dockerfile, docker-compose.yml, GCP deployment configs
- **Outputs**: Step-by-step deployment instructions
- **Must include**: Docker local (`make dev`), environment variables for production, GCP Cloud Run setup overview, cost estimate (<$50/month), health check endpoint

### FR-6: Environment Variables Reference
- **What**: Complete listing of all environment variables with descriptions
- **Inputs**: `.env.example` and `config/settings.py`
- **Outputs**: Table of all env vars, their purpose, required/optional status, defaults
- **Must include**: API keys (POLYGON_API_KEY, FRED_API_KEY, etc.), service config (ENVIRONMENT, LOG_LEVEL), feature flags

### FR-7: Documentation Validation Tests
- **What**: `tests/test_documentation.py` validates docs exist and have required content
- **Inputs**: Documentation files
- **Outputs**: Tests that verify all required docs exist, have minimum content, and cover key sections
- **Edge cases**: Tests should check for section headers, not exact content (allowing updates without breaking tests)

---

## Non-Functional Requirements

### NFR-1: Clarity
- Documentation uses simple language, avoids jargon where possible
- Code examples are copy-pasteable

### NFR-2: Completeness
- Every public API endpoint is documented
- Every environment variable is listed
- All setup steps are covered

### NFR-3: Accuracy
- All example commands actually work
- API response examples match actual Pydantic schemas

---

## Testing Strategy

| Test | Description |
|------|-------------|
| `test_readme_exists` | README.md exists at project root |
| `test_readme_has_setup_section` | README contains setup/installation section |
| `test_readme_has_testing_section` | README contains testing section |
| `test_readme_has_architecture_section` | README contains architecture overview or link |
| `test_api_reference_exists` | docs/api-reference.md exists |
| `test_api_reference_has_all_endpoints` | API docs cover all endpoints |
| `test_architecture_doc_exists` | docs/architecture.md exists |
| `test_architecture_has_agent_table` | Architecture doc lists all agents |
| `test_deployment_doc_exists` | docs/deployment.md exists |
| `test_deployment_has_docker_section` | Deployment doc covers Docker |
| `test_env_vars_documented` | All env vars from settings.py are documented |
| `test_docs_no_broken_internal_links` | No broken relative links between docs |
