# Checklist S11.2 -- Docker Compose Local Dev Stack

## Implementation Tasks

- [x] Create `docker-compose.yml` at repo root
- [x] Define `app` service with build context and dev target
- [x] Configure port mapping `8000:8080`
- [x] Add `env_file` directive for `.env`
- [x] Set default environment variables (`ENVIRONMENT`, `PORT`)
- [x] Add volume mount `.:/app` for hot reload
- [x] Override CMD with uvicorn `--reload`
- [x] Set restart policy to `unless-stopped`
- [x] Use modern Compose Specification (no `version:` key)
- [x] Set `container_name: equityiq-dev`

## Testing Tasks

- [x] Create `tests/test_docker_compose.py`
- [x] Test: service `app` exists
- [x] Test: build context is `.` and target is `dev`
- [x] Test: port mapping `8000:8080`
- [x] Test: `env_file` includes `.env`
- [x] Test: volume mount `.:/app`
- [x] Test: command contains `uvicorn` with `--reload`
- [x] Test: restart policy is `unless-stopped`
- [x] Test: container_name is `equityiq-dev`
- [x] Test: `ENVIRONMENT=development` in environment vars
- [x] Test: no deprecated `version:` key
- [x] All tests pass (13/13)

## Verification

- [x] `ruff check` passes
- [x] `ruff format --check` passes
- [x] Roadmap status updated to `done`
