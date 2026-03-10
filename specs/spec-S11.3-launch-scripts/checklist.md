# Checklist S11.3 -- Agent Launch/Stop Scripts

## Tests (Red Phase)
- [x] Create `tests/test_launch_scripts.py` with all 17 tests
- [x] Run tests -- all should FAIL (red phase)

## Implementation (Green Phase)
- [x] Create `scripts/` directory
- [x] Create `scripts/launch_agents.sh` with all agent mappings
- [x] Create `scripts/stop_agents.sh` with SIGTERM/SIGKILL logic
- [x] Make both scripts executable (`chmod +x`)
- [x] `.pids/` already in `.gitignore`
- [x] Run tests -- all 17 PASS (green phase)

## Verification
- [x] All 17 tests pass
- [x] `ruff check` passes on test file
- [x] Both scripts have proper shebang and set flags
- [x] Help flags work on both scripts
- [x] Roadmap status updated to `done`
