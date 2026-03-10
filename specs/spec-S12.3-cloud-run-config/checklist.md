# Checklist -- Spec S12.3: Cloud Run Config

## Phase 1: Setup & Dependencies
- [x] Verify S11.1 (Dockerfile) is implemented and tests pass
- [x] Create `deploy/` directory if it doesn't exist
- [x] Ensure PyYAML is available for tests (add to dev deps if needed)

## Phase 2: Tests First (TDD)
- [x] Write test file: `tests/test_cloudrun_config.py`
- [x] Write test_cloudrun_yaml_exists
- [x] Write test_cloudrun_yaml_valid (apiVersion, kind, metadata)
- [x] Write test_resource_limits (memory="1Gi", cpu="1")
- [x] Write test_autoscaling_min_max (minScale="0", maxScale="4")
- [x] Write test_container_port (8080)
- [x] Write test_concurrency (80)
- [x] Write test_request_timeout ("300")
- [x] Write test_secret_references (6 API keys)
- [x] Write test_startup_probe (/health)
- [x] Write test_image_reference (Artifact Registry pattern)
- [x] Run tests -- expect failures (Red)

## Phase 3: Implementation
- [x] Create `deploy/cloudrun.yaml` with Cloud Run service definition
- [x] Set apiVersion, kind, metadata (service name: equityiq)
- [x] Configure resource limits (1Gi memory, 1 CPU)
- [x] Configure auto-scaling annotations (0-4 instances)
- [x] Set container port 8080 and concurrency 80
- [x] Set request timeout annotation (300s)
- [x] Add Secret Manager environment variable references
- [x] Configure startup probe on /health
- [x] Set Artifact Registry image reference placeholder
- [x] Run tests -- expect pass (Green)

## Phase 4: Integration
- [x] Verify cloudrun.yaml is consistent with Dockerfile (port, health endpoint)
- [x] Verify secret names align with config/settings.py env vars
- [x] Run `make local-lint`
- [x] Run full test suite: `make local-test`

## Phase 5: Verification
- [x] All tangible outcomes checked
- [x] No hardcoded secrets in cloudrun.yaml
- [x] Image reference uses placeholder (not real project ID)
- [x] Update roadmap.md status: spec-written -> done
