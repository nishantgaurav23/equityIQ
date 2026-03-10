# Spec S11.1 -- Multi-stage Dockerfile

## Meta

| Field | Value |
|-------|-------|
| Spec ID | S11.1 |
| Phase | 11 -- Infrastructure |
| Depends On | S1.1 (pyproject.toml) |
| File(s) | `Dockerfile` |
| Status | spec-written |

## Goal

Create a multi-stage Dockerfile that supports both development (with testing/linting tools) and production (minimal, secure) builds. Single container runs all agents as async functions within one FastAPI process -- monolith-in-container approach for Cloud Run deployment under $50/month.

## Stages

### Stage 1: `base`

- **FROM** `python:3.12-slim` as `base`
- Set `PYTHONDONTWRITEBYTECODE=1` and `PYTHONUNBUFFERED=1`
- Set working directory to `/app`
- Copy `pyproject.toml` (and optionally `setup.cfg` / `setup.py` if present)
- Install runtime dependencies only: `pip install --no-cache-dir .`
- Copy the full application source code

### Stage 2: `dev`

- **FROM** `base` as `dev`
- Install dev dependencies: `pip install --no-cache-dir ".[dev]"`
- Default CMD: run pytest (`python -m pytest tests/ -v --tb=short`)
- Used for local development and CI testing

### Stage 3: `prod`

- **FROM** `base` as `prod`
- Create a non-root user `appuser` (UID 1000)
- Switch to `appuser`
- Expose port `8080` (Cloud Run default)
- Set healthcheck: `CMD curl -f http://localhost:8080/health || exit 1`
- CMD: `uvicorn app:app --host 0.0.0.0 --port 8080 --workers 1`
- Single worker because agents use `asyncio.gather()` internally

## Requirements

### R1: Base stage installs runtime deps from pyproject.toml
- Uses `pip install --no-cache-dir .` to install from pyproject.toml `[project.dependencies]`
- No `requirements.txt` file needed

### R2: Dev stage adds pytest + ruff
- Extends base stage
- Installs `[project.optional-dependencies.dev]` group
- Default command runs test suite

### R3: Prod stage runs as non-root
- Creates `appuser` with UID 1000 and no login shell
- All application files owned by `appuser`
- `USER appuser` directive before CMD

### R4: Prod stage uses uvicorn
- Runs `uvicorn app:app` on port 8080
- Single worker (async handles concurrency)
- `--host 0.0.0.0` for container networking

### R5: Prod stage has healthcheck
- HEALTHCHECK instruction pings `/health` endpoint
- Interval: 30s, timeout: 10s, retries: 3, start-period: 10s

### R6: Minimal image size
- `python:3.12-slim` base (not full python image)
- `--no-cache-dir` on all pip installs
- No unnecessary packages or build tools left in prod stage

### R7: Environment variables
- `PYTHONDONTWRITEBYTECODE=1` -- no .pyc files
- `PYTHONUNBUFFERED=1` -- real-time log output
- `PORT=8080` -- Cloud Run convention

## Tangible Outcomes

1. `docker build --target dev -t equityiq:dev .` succeeds
2. `docker build --target prod -t equityiq:prod .` succeeds
3. Prod image runs as non-root user (UID 1000)
4. Prod container exposes port 8080
5. Prod container starts uvicorn and responds to `/health`
6. Dev container can run `python -m pytest` successfully
7. No `requirements.txt` -- deps come from `pyproject.toml`

## Testing Strategy

Since Dockerfile testing requires Docker (not available in CI unit tests), we validate:

1. **Dockerfile syntax/structure tests** (`tests/test_dockerfile.py`):
   - Parse Dockerfile and verify all 3 stages exist (base, dev, prod)
   - Verify `FROM python:3.12-slim` as base image
   - Verify `USER appuser` in prod stage
   - Verify `EXPOSE 8080` in prod stage
   - Verify `HEALTHCHECK` instruction exists
   - Verify `PYTHONDONTWRITEBYTECODE` and `PYTHONUNBUFFERED` env vars set
   - Verify `--no-cache-dir` used in pip install commands
   - Verify CMD uses uvicorn with correct arguments
   - Verify non-root user creation
   - Verify no `COPY requirements.txt` (deps from pyproject.toml)

2. **Integration** (manual / CI with Docker):
   - Build dev and prod targets
   - Run prod container and check `/health` returns 200
