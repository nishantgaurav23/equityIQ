# Checklist -- Spec S11.5: Health Check Script

## Phase 1: Setup & Dependencies
- [x] Verify S11.3 (launch scripts) is implemented and tests pass
- [x] Create target file: `scripts/health_check.sh`

## Phase 2: Tests First (TDD)
- [x] Write test file: `tests/test_health_check_script.py`
- [x] Write failing tests for script existence, permissions, shebang, set flags
- [x] Write failing tests for agent definitions, curl health, flags
- [x] Write failing tests for help flag execution, summary, colors, exit logic
- [x] Run `python -m pytest tests/test_health_check_script.py -v` -- expect failures (Red)

## Phase 3: Implementation
- [x] Implement `scripts/health_check.sh` with all agent definitions
- [x] Add `-h`/`--help` flag with usage output
- [x] Add `--port PORT` single-agent check mode
- [x] Add `--timeout SECONDS` configurable timeout
- [x] Add `--json` machine-readable output mode
- [x] Add color-coded status table output
- [x] Add summary line and exit code logic
- [x] Make script executable (`chmod +x`)
- [x] Run tests -- expect pass (Green)

## Phase 4: Integration
- [x] Verify script works alongside launch_agents.sh and stop_agents.sh
- [x] Run full test suite: 806 tests pass

## Phase 5: Verification
- [x] All tangible outcomes checked
- [x] Script has proper shebang and set flags
- [x] No hardcoded secrets
- [x] Works on both macOS and Linux (POSIX-compatible)
- [x] Update roadmap.md status: spec-written -> done
