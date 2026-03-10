# Checklist -- Spec S12.2: GitHub Actions CD Pipeline

## Phase 1: Setup & Dependencies
- [x] Verify S12.1 (GitHub Actions CI) is implemented and tests pass
- [x] Verify S11.1 (Dockerfile) is implemented and tests pass
- [x] Confirm `.github/workflows/` directory exists

## Phase 2: Tests First (TDD)
- [x] Write test file: `tests/test_cd_workflow.py`
- [x] Write failing test: `test_deploy_workflow_exists`
- [x] Write failing test: `test_deploy_trigger_main_only`
- [x] Write failing test: `test_deploy_uses_wif_auth`
- [x] Write failing test: `test_deploy_docker_build_push`
- [x] Write failing test: `test_deploy_cloud_run_step`
- [x] Write failing test: `test_deploy_concurrency_group`
- [x] Write failing test: `test_deploy_no_hardcoded_secrets`
- [x] Write failing test: `test_deploy_depends_on_ci`
- [x] Write failing test: `test_deploy_image_tags`
- [x] Run tests -- expect failures (Red)

## Phase 3: Implementation
- [x] Create `.github/workflows/deploy.yml`
- [x] Add workflow_run trigger (CI must pass on main)
- [x] Add concurrency group with cancel-in-progress
- [x] Add CI gate via workflow_run on "CI" workflow
- [x] Add Workload Identity Federation auth step (google-github-actions/auth@v2)
- [x] Add Docker build and push step (prod stage, SHA + latest tags)
- [x] Add Cloud Run deploy step (google-github-actions/deploy-cloudrun@v2)
- [x] Reference all GCP config via GitHub secrets
- [x] Run tests -- expect pass (Green)

## Phase 4: Integration
- [x] Verify deploy.yml is valid YAML
- [x] Run ruff on test file
- [x] Run full test suite (1395 passed)

## Phase 5: Verification
- [x] All tangible outcomes checked
- [x] No hardcoded secrets or project IDs
- [x] Workflow uses latest stable action versions
- [x] Update roadmap.md status: pending -> done
