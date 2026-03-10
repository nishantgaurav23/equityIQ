# Checklist S11.1 -- Multi-stage Dockerfile

## Implementation Tasks

- [x] Write `Dockerfile` with 3 stages (base, dev, prod)
- [x] Base stage: Python 3.12-slim, env vars, install deps from pyproject.toml
- [x] Dev stage: extends base, installs dev deps, CMD runs pytest
- [x] Prod stage: non-root user, EXPOSE 8080, HEALTHCHECK, uvicorn CMD
- [x] Write `tests/test_dockerfile.py` with Dockerfile structure validation
- [x] All tests pass (`python -m pytest tests/test_dockerfile.py -v`) -- 23/23
- [x] Ruff lint clean (`ruff check tests/test_dockerfile.py`)
- [x] Update `roadmap.md` status to `done`
