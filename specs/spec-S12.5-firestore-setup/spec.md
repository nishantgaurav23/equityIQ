# Spec S12.5 -- Firestore Database Setup

## Overview
Shell script to create and configure a Google Cloud Firestore database for EquityIQ production deployment. The script provisions a Firestore database in Native mode, creates the `verdicts` collection structure, and sets up composite indexes required for efficient querying (ticker + created_at). This supports the FirestoreVault backend (`memory/firestore_vault.py`) which is activated when `ENVIRONMENT=production`.

## Dependencies
- S5.3 (Firestore backend) -- defines the Firestore collection and query patterns used by the application

## Target Location
- `deploy/setup-firestore.sh` -- main setup script

---

## Functional Requirements

### FR-1: Firestore Database Creation
- **What**: Bash script that creates a Firestore database in Native mode for the GCP project
- **Inputs**: GCP_PROJECT_ID (from env or argument), optional `--region` flag (default: us-central1)
- **Outputs**: Creates Firestore database in Native mode; prints status
- **Edge cases**: Database already exists (skip with message), missing gcloud CLI (error), missing project ID (error), Firestore API not enabled (enable it or error with guidance)

### FR-2: Composite Index Creation
- **What**: Create composite indexes required by FirestoreVault queries
- **Inputs**: GCP_PROJECT_ID
- **Outputs**: Creates composite index on `verdicts` collection: `ticker` (ASC) + `created_at` (DESC)
- **Edge cases**: Index already exists (skip), index creation in progress (report status)

### FR-3: Idempotent Execution
- **What**: Script can be run multiple times safely without errors or duplicate resources
- **Inputs**: Same as FR-1
- **Outputs**: Skips existing database/indexes, creates only missing resources
- **Edge cases**: Partial previous run (completes remaining setup)

### FR-4: Firestore API Enablement
- **What**: Ensure the Firestore API is enabled on the GCP project before creating resources
- **Inputs**: GCP_PROJECT_ID
- **Outputs**: Enables `firestore.googleapis.com` if not already enabled
- **Edge cases**: API already enabled (idempotent), insufficient permissions (error with guidance)

### FR-5: IAM Permissions Check
- **What**: Verify the Cloud Run service account has `datastore.user` role for Firestore access
- **Inputs**: GCP_PROJECT_ID, optional `--service-account` flag
- **Outputs**: Grants `roles/datastore.user` to the Cloud Run service account
- **Edge cases**: Binding already exists (idempotent), custom service account specified

### FR-6: Verification
- **What**: Verify Firestore database exists, is in Native mode, and indexes are ready
- **Inputs**: GCP_PROJECT_ID
- **Outputs**: Status report showing database mode, collection info, index status
- **Edge cases**: Index still building (report BUILDING status)

---

## Tangible Outcomes

- [ ] **Outcome 1**: `deploy/setup-firestore.sh` exists and is executable
- [ ] **Outcome 2**: Script creates Firestore database in Native mode
- [ ] **Outcome 3**: Script creates composite index on `verdicts` collection (ticker ASC + created_at DESC)
- [ ] **Outcome 4**: Script is idempotent -- running twice produces no errors
- [ ] **Outcome 5**: Script enables Firestore API if not already enabled
- [ ] **Outcome 6**: Script grants Cloud Run service account `datastore.user` role
- [ ] **Outcome 7**: Script supports `--help` flag with usage instructions
- [ ] **Outcome 8**: Script outputs clear status messages for each operation
- [ ] **Outcome 9**: Collection name (`verdicts`) matches `memory/firestore_vault.py` `_COLLECTION` constant

---

## Test-Driven Requirements

### Tests to Write First (Red -> Green)
1. **test_setup_firestore_script_exists**: Verify `deploy/setup-firestore.sh` exists and is executable
2. **test_setup_firestore_shellcheck**: Run shellcheck on the script (if available)
3. **test_setup_firestore_project_id_required**: Verify script validates GCP_PROJECT_ID is set
4. **test_setup_firestore_gcloud_check**: Verify script checks for gcloud CLI availability
5. **test_setup_firestore_native_mode**: Verify script creates database in Native mode (FIRESTORE_NATIVE)
6. **test_setup_firestore_collection_name**: Verify script references `verdicts` collection matching firestore_vault.py
7. **test_setup_firestore_composite_index**: Verify script creates composite index on ticker + created_at
8. **test_setup_firestore_api_enablement**: Verify script enables firestore.googleapis.com API
9. **test_setup_firestore_iam_binding**: Verify script includes IAM binding for datastore.user role
10. **test_setup_firestore_idempotent**: Verify script checks for existing resources before creating
11. **test_setup_firestore_help_flag**: Verify script supports `--help` flag
12. **test_setup_firestore_region_default**: Verify script uses us-central1 as default region

### Mocking Strategy
- Tests are script-level validation (parsing, shellcheck) -- no GCP calls needed
- Use subprocess to run script with `--help` or `--dry-run` flag
- Parse script content to verify gcloud commands and collection names
- Cross-reference collection name with `memory/firestore_vault.py`

### Coverage Expectation
- All script behaviors validated via parsing and dry-run tests
- Collection name cross-referenced with firestore_vault.py

---

## References
- roadmap.md -- Phase 12: GCP Deployment
- design.md -- GCP deployment architecture
- memory/firestore_vault.py -- FirestoreVault implementation using `verdicts` collection
- deploy/cloudrun.yaml -- Cloud Run service config (ENVIRONMENT=production)
- config/settings.py -- GCP_PROJECT_ID setting
