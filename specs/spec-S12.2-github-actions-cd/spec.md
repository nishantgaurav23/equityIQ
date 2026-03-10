# Spec S12.2 -- GitHub Actions CD Pipeline

## Overview
Continuous Deployment pipeline that triggers on push to `main` branch. Builds a Docker image, pushes it to Google Artifact Registry, and deploys to Cloud Run. Uses Workload Identity Federation for keyless authentication (no service account JSON keys). The workflow runs only after CI tests and lint pass.

## Dependencies
- S12.1 (GitHub Actions CI) -- CI workflow must exist and pass before CD runs
- S11.1 (Dockerfile) -- Multi-stage Dockerfile must exist for building the image

## Target Location
`.github/workflows/deploy.yml`

---

## Functional Requirements

### FR-1: Trigger on push to main only
- **What**: Workflow triggers only on push events to the `main` branch, not on PRs or other branches
- **Inputs**: Push event to `main`
- **Outputs**: Workflow run starts
- **Edge cases**: Should not trigger on PR merges to non-main branches

### FR-2: CI gate before deployment
- **What**: CD workflow waits for CI workflow to complete successfully before proceeding. Uses `workflow_run` trigger or `needs` dependency on CI job
- **Inputs**: CI workflow completion status
- **Outputs**: CD proceeds only if CI passed
- **Edge cases**: If CI fails, CD should not run

### FR-3: Authenticate via Workload Identity Federation
- **What**: Use `google-github-actions/auth@v2` with Workload Identity Federation for keyless GCP authentication. No service account JSON keys stored in secrets
- **Inputs**: GitHub OIDC token, GCP project configuration (via GitHub secrets: `GCP_PROJECT_ID`, `GCP_WIF_PROVIDER`, `GCP_WIF_SERVICE_ACCOUNT`)
- **Outputs**: Authenticated gcloud session
- **Edge cases**: Auth failure should fail the workflow with a clear error

### FR-4: Build and push Docker image to Artifact Registry
- **What**: Build the `prod` stage of the multi-stage Dockerfile and push to Artifact Registry. Tag with both `latest` and the git SHA for traceability
- **Inputs**: Dockerfile (prod target), source code
- **Outputs**: Docker image at `{REGION}-docker.pkg.dev/{PROJECT_ID}/{REPO}/{IMAGE}:{TAG}`
- **Edge cases**: Build failure should fail fast; image should use `prod` stage only

### FR-5: Deploy to Cloud Run
- **What**: Deploy the pushed image to Cloud Run using `google-github-actions/deploy-cloudrun@v2`. Configure region, service name, and allow unauthenticated access (public API)
- **Inputs**: Docker image URI, Cloud Run service configuration
- **Outputs**: Updated Cloud Run service running the new image
- **Edge cases**: Deployment failure should fail the workflow; rollback is handled by Cloud Run revision history

### FR-6: Concurrency control
- **What**: Only one deployment runs at a time. If a new push arrives while deploying, cancel the in-progress deployment
- **Inputs**: Concurrent push events to main
- **Outputs**: Only the latest push deploys

### FR-7: Environment variables via GitHub secrets
- **What**: All GCP configuration passed via GitHub repository secrets, never hardcoded
- **Inputs**: `GCP_PROJECT_ID`, `GCP_REGION`, `GCP_WIF_PROVIDER`, `GCP_WIF_SERVICE_ACCOUNT`, `GCP_ARTIFACT_REPO`, `CLOUD_RUN_SERVICE`
- **Outputs**: Secrets injected into workflow steps

---

## Tangible Outcomes

- [ ] **Outcome 1**: `.github/workflows/deploy.yml` exists and is valid YAML
- [ ] **Outcome 2**: Workflow triggers only on push to `main` branch
- [ ] **Outcome 3**: Workflow uses Workload Identity Federation (no service account keys)
- [ ] **Outcome 4**: Docker image built from `prod` stage and pushed to Artifact Registry with SHA tag
- [ ] **Outcome 5**: Cloud Run deployment step uses `google-github-actions/deploy-cloudrun@v2`
- [ ] **Outcome 6**: Concurrency group ensures only one deploy runs at a time
- [ ] **Outcome 7**: All GCP config values reference GitHub secrets, nothing hardcoded

---

## Test-Driven Requirements

### Tests to Write First (Red -> Green)
1. **test_deploy_workflow_exists**: Verify `.github/workflows/deploy.yml` exists and is valid YAML
2. **test_deploy_trigger_main_only**: Parse workflow YAML, confirm trigger is push to main only
3. **test_deploy_uses_wif_auth**: Verify auth step uses `google-github-actions/auth@v2` with workload_identity_provider
4. **test_deploy_docker_build_push**: Verify docker build/push step targets Artifact Registry with SHA tagging
5. **test_deploy_cloud_run_step**: Verify deploy step uses `google-github-actions/deploy-cloudrun@v2`
6. **test_deploy_concurrency_group**: Verify concurrency group is set with cancel-in-progress
7. **test_deploy_no_hardcoded_secrets**: Scan workflow for hardcoded project IDs, regions, or service account emails
8. **test_deploy_depends_on_ci**: Verify CD has a dependency gate on CI passing
9. **test_deploy_image_tags**: Verify image is tagged with both `latest` and git SHA

### Mocking Strategy
- No external mocks needed -- tests validate YAML structure and content
- Use `yaml.safe_load()` to parse the workflow file
- Use regex to scan for hardcoded secrets patterns

### Coverage Expectation
- All workflow steps validated for correct action versions and parameters
- Security: no hardcoded credentials or project identifiers

---

## References
- roadmap.md Phase 12
- design.md GCP Deployment Architecture
- `.github/workflows/ci.yml` (existing CI workflow)
- Google Cloud docs: Workload Identity Federation, Cloud Run, Artifact Registry
