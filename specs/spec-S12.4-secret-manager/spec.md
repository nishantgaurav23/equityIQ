# Spec S12.4 -- GCP Secret Manager Setup

## Overview
Shell script to create and manage GCP Secret Manager secrets for EquityIQ. The script provisions all required API keys (GOOGLE_API_KEY, POLYGON_API_KEY, FRED_API_KEY, NEWS_API_KEY, SERPER_API_KEY, TAVILY_API_KEY) as Secret Manager secrets. Cloud Run mounts these as environment variables via `secretKeyRef` in the service YAML (already configured in `deploy/cloudrun.yaml`).

## Dependencies
- S1.3 (pydantic-settings) -- defines the env var names used by the application

## Target Location
- `deploy/setup-secrets.sh` -- main setup script
- `deploy/verify-secrets.sh` -- verification script (optional helper)

---

## Functional Requirements

### FR-1: Secret Creation Script
- **What**: Bash script that creates GCP Secret Manager secrets for all required API keys
- **Inputs**: GCP_PROJECT_ID (from env or argument), optional `--from-env` flag to populate from current env vars
- **Outputs**: Creates secrets in GCP Secret Manager; prints status for each secret
- **Secrets to create**: GOOGLE_API_KEY, POLYGON_API_KEY, FRED_API_KEY, NEWS_API_KEY, SERPER_API_KEY, TAVILY_API_KEY
- **Edge cases**: Secret already exists (skip with warning), missing gcloud CLI (error), missing project ID (error), insufficient permissions (error with guidance)

### FR-2: Idempotent Execution
- **What**: Script can be run multiple times safely without duplicating or overwriting existing secrets
- **Inputs**: Same as FR-1
- **Outputs**: Skips existing secrets, creates only missing ones
- **Edge cases**: Partial previous run (creates remaining secrets)

### FR-3: Secret Value Population
- **What**: When `--from-env` flag is provided, populate secret values from current environment variables
- **Inputs**: `--from-env` flag, environment variables matching secret names
- **Outputs**: Creates secret versions with values from env vars
- **Edge cases**: Env var is empty (skip with warning), env var not set (skip with warning)

### FR-4: Cloud Run IAM Binding
- **What**: Grant the Cloud Run service account `secretmanager.secretAccessor` role on the project
- **Inputs**: GCP_PROJECT_ID, service account email (derived or passed)
- **Outputs**: IAM binding added
- **Edge cases**: Binding already exists (idempotent), custom service account specified via `--service-account` flag

### FR-5: Verification
- **What**: Verify all required secrets exist and Cloud Run can access them
- **Inputs**: GCP_PROJECT_ID
- **Outputs**: Status report listing each secret and its existence/version count
- **Edge cases**: Secret exists but has no versions (warning)

---

## Tangible Outcomes

- [ ] **Outcome 1**: `deploy/setup-secrets.sh` exists, is executable, and passes shellcheck
- [ ] **Outcome 2**: Script creates all 6 required secrets when run against a GCP project
- [ ] **Outcome 3**: Script is idempotent -- running twice produces no errors or duplicates
- [ ] **Outcome 4**: `--from-env` flag populates secrets from environment variables
- [ ] **Outcome 5**: Script grants Cloud Run service account access to secrets
- [ ] **Outcome 6**: Script outputs clear status messages for each operation
- [ ] **Outcome 7**: Secret names match those in `deploy/cloudrun.yaml` secretKeyRef entries

---

## Test-Driven Requirements

### Tests to Write First (Red -> Green)
1. **test_setup_secrets_script_exists**: Verify `deploy/setup-secrets.sh` exists and is executable
2. **test_setup_secrets_shellcheck**: Run shellcheck on the script (if available)
3. **test_setup_secrets_required_secrets**: Parse script to verify all 6 secret names are included
4. **test_setup_secrets_idempotent_check**: Verify script checks for existing secrets before creating
5. **test_setup_secrets_project_id_required**: Verify script validates GCP_PROJECT_ID is set
6. **test_setup_secrets_gcloud_check**: Verify script checks for gcloud CLI availability
7. **test_setup_secrets_from_env_flag**: Verify script supports `--from-env` flag
8. **test_setup_secrets_iam_binding**: Verify script includes IAM binding for secretAccessor role
9. **test_secrets_match_cloudrun_yaml**: Verify secret names in script match `deploy/cloudrun.yaml`
10. **test_setup_secrets_help_flag**: Verify script supports `--help` flag

### Mocking Strategy
- Tests are script-level validation (parsing, shellcheck) -- no GCP calls needed
- Use subprocess to run script with `--help` or `--dry-run` flag
- Compare secret names against cloudrun.yaml programmatically

### Coverage Expectation
- All script behaviors validated via parsing and dry-run tests
- Secret names cross-referenced with cloudrun.yaml

---

## References
- roadmap.md -- Phase 12: GCP Deployment
- design.md -- GCP deployment architecture
- deploy/cloudrun.yaml -- Cloud Run service config with secretKeyRef entries
- config/settings.py -- Env var names used by application
