# Spec S12.3 -- Cloud Run Config

## Overview
GCP Cloud Run service configuration file for deploying EquityIQ as a single container. Defines resource limits (1GB memory, 1 CPU), auto-scaling (0-4 instances), networking (port 8080, concurrency 80), and timeout settings (300s). All 7 agents run as async functions inside a single FastAPI container -- no inter-service HTTP calls.

## Dependencies
- S11.1 (Dockerfile) -- must have a production-ready Docker image to deploy

## Target Location
- `deploy/cloudrun.yaml` -- Cloud Run service YAML configuration

---

## Functional Requirements

### FR-1: Valid Cloud Run Service YAML
- **What**: `deploy/cloudrun.yaml` must be a valid Cloud Run service definition using the `serving.knative.dev/v1` API
- **Inputs**: N/A (static configuration file)
- **Outputs**: YAML file parseable by `gcloud run services replace`
- **Edge cases**: YAML syntax errors, missing required fields

### FR-2: Resource Limits
- **What**: Container must specify memory limit of 1GB and CPU limit of 1
- **Inputs**: N/A
- **Outputs**: `resources.limits.memory: "1Gi"`, `resources.limits.cpu: "1"`
- **Edge cases**: Ensure units are correct (Gi not GB, string "1" for cpu)

### FR-3: Auto-Scaling Configuration
- **What**: Min instances: 0 (scale to zero), Max instances: 4
- **Inputs**: N/A
- **Outputs**: Annotations `autoscaling.knative.dev/minScale: "0"`, `autoscaling.knative.dev/maxScale: "4"`
- **Edge cases**: Values must be strings in annotations

### FR-4: Networking Configuration
- **What**: Container port 8080, max concurrency 80 requests per instance
- **Inputs**: N/A
- **Outputs**: `containerPort: 8080`, `containerConcurrency: 80`
- **Edge cases**: Port must match Dockerfile EXPOSE and uvicorn --port

### FR-5: Timeout and Startup Configuration
- **What**: Request timeout 300s (5 minutes) to accommodate full 7-agent parallel analysis
- **Inputs**: N/A
- **Outputs**: Annotation `run.googleapis.com/request-timeout: "300"`
- **Edge cases**: Must be string value in annotations

### FR-6: Secret Manager Integration Placeholders
- **What**: Environment variables referencing GCP Secret Manager for all API keys (GOOGLE_API_KEY, POLYGON_API_KEY, FRED_API_KEY, NEWS_API_KEY, SERPER_API_KEY, TAVILY_API_KEY)
- **Inputs**: N/A
- **Outputs**: `valueFrom.secretKeyRef` entries for each secret
- **Edge cases**: Secret names must match what S12.4 will create

### FR-7: Health Check / Startup Probe
- **What**: Configure startup probe hitting `/health` endpoint
- **Inputs**: N/A
- **Outputs**: Startup probe with HTTP GET on `/health`, port 8080
- **Edge cases**: Must use the correct health endpoint path

### FR-8: Container Image Reference
- **What**: Image reference uses Artifact Registry path pattern
- **Inputs**: N/A
- **Outputs**: `image: REGION-docker.pkg.dev/PROJECT_ID/equityiq/equityiq:latest` (placeholder)
- **Edge cases**: CD pipeline (S12.2) substitutes actual values at deploy time

---

## Tangible Outcomes

- [ ] **Outcome 1**: `deploy/cloudrun.yaml` exists and is valid YAML
- [ ] **Outcome 2**: Resource limits are 1Gi memory, 1 CPU
- [ ] **Outcome 3**: Auto-scaling is 0-4 instances
- [ ] **Outcome 4**: Port is 8080, concurrency is 80
- [ ] **Outcome 5**: Request timeout is 300s
- [ ] **Outcome 6**: Secret Manager references for all 6 API keys
- [ ] **Outcome 7**: Startup probe configured for /health endpoint
- [ ] **Outcome 8**: Tests validate all configuration values programmatically

---

## Test-Driven Requirements

### Tests to Write First (Red -> Green)
1. **test_cloudrun_yaml_exists**: Verify `deploy/cloudrun.yaml` exists
2. **test_cloudrun_yaml_valid**: Parse YAML and verify it's a valid Cloud Run service definition (apiVersion, kind, metadata)
3. **test_resource_limits**: Verify memory="1Gi" and cpu="1"
4. **test_autoscaling_min_max**: Verify minScale="0" and maxScale="4"
5. **test_container_port**: Verify containerPort is 8080
6. **test_concurrency**: Verify containerConcurrency is 80
7. **test_request_timeout**: Verify timeout annotation is "300"
8. **test_secret_references**: Verify all 6 API key secrets are referenced
9. **test_startup_probe**: Verify startup probe on /health
10. **test_image_reference**: Verify image uses Artifact Registry pattern

### Mocking Strategy
- No external mocking needed -- this spec tests a static YAML configuration file
- Tests use PyYAML to parse and validate the file

### Coverage Expectation
- All configuration values validated by at least one test
- Edge cases: YAML structure, correct field paths, correct value types

---

## References
- roadmap.md -- S12.3 spec definition
- design.md -- Cloud Run deployment strategy, cost estimates
- Dockerfile -- port 8080, health check, uvicorn CMD
- `.github/workflows/deploy.yml` -- CD pipeline that deploys using this config
