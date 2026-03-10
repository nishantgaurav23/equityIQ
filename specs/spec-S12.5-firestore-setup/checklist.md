# Checklist -- Spec S12.5: Firestore Database Setup

## Phase 1: Setup & Dependencies
- [x] Verify S5.3 (Firestore backend) is implemented
- [x] Review `memory/firestore_vault.py` for collection name and query patterns
- [x] Review `deploy/cloudrun.yaml` for ENVIRONMENT=production setting
- [x] Review `config/settings.py` for GCP_PROJECT_ID

## Phase 2: Tests First (TDD)
- [x] Write test file: `tests/test_firestore_setup.py`
- [x] Write test: script exists and is executable
- [x] Write test: shellcheck passes (if shellcheck available)
- [x] Write test: script requires GCP_PROJECT_ID
- [x] Write test: script checks for gcloud CLI
- [x] Write test: script creates database in Native mode
- [x] Write test: script references `verdicts` collection
- [x] Write test: script creates composite index on ticker + created_at
- [x] Write test: script enables Firestore API
- [x] Write test: script includes IAM binding for datastore.user
- [x] Write test: script is idempotent (checks before creating)
- [x] Write test: script supports `--help` flag
- [x] Write test: script uses us-central1 as default region
- [x] Run tests -- expect failures (Red)

## Phase 3: Implementation
- [x] Create `deploy/setup-firestore.sh` with shebang and strict mode
- [x] Implement `--help` flag with usage instructions
- [x] Implement GCP project ID validation
- [x] Implement gcloud CLI check
- [x] Implement Firestore API enablement
- [x] Implement database creation in Native mode
- [x] Implement composite index creation (ticker ASC + created_at DESC)
- [x] Implement idempotency checks (existing database, existing indexes)
- [x] Implement IAM binding for Cloud Run service account
- [x] Implement `--region` flag (default: us-central1)
- [x] Implement status output for each operation
- [x] Implement verification/status report
- [x] Make script executable (`chmod +x`)
- [x] Run tests -- expect pass (Green)
- [x] Refactor if needed

## Phase 4: Integration
- [x] Verify collection name matches `memory/firestore_vault.py` _COLLECTION
- [x] Run shellcheck on script (skipped - shellcheck not installed)
- [x] Run full test suite

## Phase 5: Verification
- [x] All tangible outcomes checked
- [x] No hardcoded project IDs or secrets
- [x] Script uses strict mode (`set -euo pipefail`)
- [x] Script is well-documented with inline comments
- [x] Update roadmap.md status: pending -> done
