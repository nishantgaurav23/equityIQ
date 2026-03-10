# Spec S11.2 -- Docker Compose Local Dev Stack

## Meta

| Field | Value |
|-------|-------|
| Spec ID | S11.2 |
| Phase | 11 -- Infrastructure |
| Depends On | S11.1 (Dockerfile) |
| File(s) | `docker-compose.yml` |
| Status | done |

## Goal

Create a `docker-compose.yml` for local development that builds from the Dockerfile dev stage, exposes port 8000, loads environment from `.env`, and mounts the source code as a volume for hot reload.

## Requirements

### R1: Service definition -- `app`

- Service named `app`
- Build context: `.` (repo root)
- Build target: `dev` (Dockerfile dev stage)
- Container name: `equityiq-dev`

### R2: Port mapping

- Map host port `8000` to container port `8080`
- Host port 8000 matches the FastAPI gateway convention from design.md
- Container port 8080 matches the Dockerfile EXPOSE

### R3: Environment configuration

- Load environment variables from `.env` file via `env_file` directive
- Set `ENVIRONMENT=development` as a default environment variable
- Set `PORT=8080` to match Dockerfile convention

### R4: Volume mount for hot reload

- Mount current directory (`.`) to `/app` in the container
- This enables live code changes without rebuilding
- Exclude `venv/` and `__pycache__/` via `.dockerignore` (handled by S11.4)

### R5: Override CMD for development

- Override default CMD (pytest) with uvicorn in reload mode
- Command: `uvicorn app:app --host 0.0.0.0 --port 8080 --reload`
- `--reload` enables hot reload for development

### R6: Restart policy

- Set `restart: unless-stopped` for development convenience
- Container auto-restarts on crash but stays down on manual stop

### R7: Compose file version

- Use Compose Specification (no `version:` key -- modern compose)
- Compatible with `docker compose` (v2) CLI

## Tangible Outcomes

1. `docker compose up --build` starts the dev server on port 8000
2. Code changes on host are reflected in container without rebuild
3. Environment variables loaded from `.env` file
4. `docker compose down` cleanly stops the stack
5. Container runs uvicorn with `--reload` for hot reload
6. Service builds from Dockerfile `dev` target

## Testing Strategy

Since docker-compose testing requires Docker runtime, we validate structure:

1. **docker-compose.yml syntax/structure tests** (`tests/test_docker_compose.py`):
   - Parse YAML and verify service `app` exists
   - Verify build context is `.` and target is `dev`
   - Verify port mapping `8000:8080`
   - Verify `env_file` includes `.env`
   - Verify volume mount `.:/app`
   - Verify command contains `uvicorn` with `--reload`
   - Verify `restart: unless-stopped`
   - Verify container_name is `equityiq-dev`
   - Verify `ENVIRONMENT=development` in environment vars
   - Verify no deprecated `version:` key (modern compose spec)
