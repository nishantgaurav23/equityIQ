# Checklist -- Spec S12.4: GCP Secret Manager Setup

## Phase 1: Setup & Dependencies
- [x] Verify S1.3 (pydantic-settings) is implemented
- [x] Review `deploy/cloudrun.yaml` for secret names referenced
- [x] Review `config/settings.py` for all API key env vars

## Phase 2: Tests First (TDD)
- [x] Write test file: `tests/test_secret_manager.py`
- [x] Write test: script exists and is executable
- [x] Write test: shellcheck passes (if shellcheck available)
- [x] Write test: all 6 required secrets are referenced in script
- [x] Write test: script checks for existing secrets (idempotency)
- [x] Write test: script requires GCP_PROJECT_ID
- [x] Write test: script checks for gcloud CLI
- [x] Write test: script supports `--from-env` flag
- [x] Write test: script includes IAM binding command
- [x] Write test: secret names match cloudrun.yaml
- [x] Write test: script supports `--help` flag
- [x] Run tests -- expect failures (Red)

## Phase 3: Implementation
- [x] Create `deploy/setup-secrets.sh` with shebang and strict mode
- [x] Implement `--help` flag with usage instructions
- [x] Implement GCP project ID validation
- [x] Implement gcloud CLI check
- [x] Implement secret creation for all 6 API keys
- [x] Implement idempotency (check before create)
- [x] Implement `--from-env` flag for populating secret values
- [x] Implement IAM binding for Cloud Run service account
- [x] Implement status output for each operation
- [x] Make script executable (`chmod +x`)
- [x] Run tests -- expect pass (Green)
- [x] Refactor if needed

## Phase 4: Integration
- [x] Verify secret names match `deploy/cloudrun.yaml` secretKeyRef entries
- [x] Run ruff/shellcheck on any Python/shell files
- [x] Run full test suite

## Phase 5: Verification
- [x] All tangible outcomes checked
- [x] No hardcoded secrets in script
- [x] Script uses strict mode (`set -euo pipefail`)
- [x] Script is well-documented with inline comments
- [x] Update roadmap.md status: spec-written -> done
