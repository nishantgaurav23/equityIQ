# Spec S11.4 -- Docker Ignore Rules

## Meta

| Field | Value |
|-------|-------|
| Spec ID | S11.4 |
| Phase | 11 -- Infrastructure |
| Location | `.dockerignore` |
| Depends On | -- (none) |
| Status | spec-written |

## Goal

Create a `.dockerignore` file that excludes unnecessary files and directories from the Docker build context. This reduces build time, image size, and prevents sensitive files (like `.env`) from leaking into the container.

## Requirements

### R1: Exclude development and virtual environment files
- `venv/` -- Python virtual environment
- `.venv/` -- Alternative venv location
- `__pycache__/` -- Python bytecode cache
- `*.pyc` -- Compiled Python files
- `*.pyo` -- Optimized Python files
- `.pytest_cache/` -- Pytest cache
- `.ruff_cache/` -- Ruff linter cache
- `*.egg-info/` -- Python package metadata
- `.mypy_cache/` -- Mypy type checker cache

### R2: Exclude secrets and environment files
- `.env` -- Local environment variables (contains API keys)
- `.env.*` -- Environment variants (e.g., `.env.local`, `.env.production`)
- `*.pem` -- SSL certificates
- `*.key` -- Private keys

### R3: Exclude version control and IDE files
- `.git/` -- Git repository data
- `.gitignore` -- Git ignore rules (not needed in container)
- `.vscode/` -- VS Code settings
- `.idea/` -- JetBrains IDE settings
- `.claude/` -- Claude Code settings

### R4: Exclude documentation and non-runtime files
- `docs/` -- Documentation
- `notebooks/` -- Jupyter notebooks
- `specs/` -- Spec files (development artifacts)
- `*.md` -- Markdown files (README, roadmap, design, etc.)
- `LICENSE` -- License file
- `design.md` -- Architecture design doc
- `roadmap.md` -- Development roadmap

### R5: Exclude test and evaluation files (for prod stage)
- `tests/` -- Test suite (not needed in production image)
- `evaluation/` -- Evaluation framework

### R6: Exclude data and frontend files
- `data/*.db` -- SQLite database files
- `data/models/` -- Trained model files (downloaded at runtime or baked separately)
- `frontend/` -- Next.js frontend (built separately)
- `frontend/node_modules/` -- Node.js dependencies

### R7: Exclude Docker and CI/CD files
- `Dockerfile` -- The Dockerfile itself
- `docker-compose.yml` -- Compose file
- `docker-compose*.yml` -- Compose variants
- `.dockerignore` -- This file
- `.github/` -- GitHub Actions workflows
- `deploy/` -- Deployment configs (used externally, not in container)

### R8: Exclude scripts directory (optional, keep if needed for container)
- `scripts/` -- Launch/stop scripts (used outside container)

### R9: Re-include essential files
Use `!` negation pattern to ensure critical files are NOT excluded:
- `!requirements.txt` -- If generated
- `!pyproject.toml` -- Dependency declaration
- Note: The Dockerfile COPY commands determine what enters the image; `.dockerignore` filters the build context sent to the Docker daemon.

## Tangible Outcomes

1. `.dockerignore` file exists at project root
2. Running `docker build` sends a minimal build context (< 5MB excluding data/)
3. No `.env`, `.git/`, `venv/`, or `__pycache__/` in the build context
4. Test verifies the file exists and contains required exclusion patterns

## Test Plan

- `tests/test_dockerignore.py`:
  - Test that `.dockerignore` file exists
  - Test that all required exclusion patterns are present
  - Test that the file is valid (no syntax errors, proper format)
  - Test that `.env` is excluded (security-critical)
  - Test that `venv/` is excluded
  - Test that `.git/` is excluded
