# Spec S11.3 -- Agent Launch/Stop Scripts

## Meta
| Field | Value |
|-------|-------|
| Spec ID | S11.3 |
| Title | Agent Launch/Stop Scripts |
| Phase | 11 -- Infrastructure |
| Depends on | S1.2 (Makefile) |
| Produces | `scripts/launch_agents.sh`, `scripts/stop_agents.sh` |
| Status | spec-written |

## 1. Purpose

Provide shell scripts to start all EquityIQ agents on their designated ports (8000-8007) and stop them cleanly. PID management enables reliable process tracking and cleanup.

## 2. Background

In local development and Docker containers, we need a way to start the MarketConductor (port 8000) and all 7 specialist agents (ports 8001-8007) as background processes, track their PIDs, and stop them on demand. These scripts support `make local-dev` and container entrypoints.

## 3. Deliverables

### 3.1 `scripts/launch_agents.sh`

Bash script that:
1. Creates `.pids/` directory if it doesn't exist
2. Starts each agent as a background uvicorn process on its designated port
3. Writes each process PID to `.pids/{agent_name}.pid`
4. Waits briefly (2s) then performs a basic health check (curl each port)
5. Reports launch status table (agent name, port, PID, status)
6. Exits with code 0 if all agents started, 1 if any failed

**Agent mapping:**
| Agent | Module | Port |
|-------|--------|------|
| market_conductor | agents.market_conductor | 8000 |
| valuation_scout | agents.valuation_scout | 8001 |
| momentum_tracker | agents.momentum_tracker | 8002 |
| pulse_monitor | agents.pulse_monitor | 8003 |
| economy_watcher | agents.economy_watcher | 8004 |
| compliance_checker | agents.compliance_checker | 8005 |
| signal_synthesizer | agents.signal_synthesizer | 8006 |
| risk_guardian | agents.risk_guardian | 8007 |

**Script behavior:**
- Uses `uvicorn {module}:app --host 0.0.0.0 --port {port} &` for each agent
- Captures PID via `$!`
- PID files: `.pids/{agent_name}.pid` (one PID per file)
- Health check: `curl -sf http://localhost:{port}/health` (timeout 2s)
- Color-coded output: green for UP, red for DOWN
- If `--no-health-check` flag is passed, skip the health check step

### 3.2 `scripts/stop_agents.sh`

Bash script that:
1. Reads all PID files from `.pids/`
2. Sends SIGTERM to each process
3. Waits up to 5 seconds for graceful shutdown
4. If process still running after 5s, sends SIGKILL
5. Removes PID files after successful stop
6. Reports stop status table
7. Cleans up `.pids/` directory if empty

**Script behavior:**
- Handles missing `.pids/` directory gracefully (just report "no agents running")
- Handles stale PID files (process already dead) gracefully
- `--force` flag: skip SIGTERM, go straight to SIGKILL
- Exit code 0 always (stop is best-effort)

### 3.3 Both Scripts

- Must have `#!/usr/bin/env bash` shebang
- Must use `set -euo pipefail`
- Must be executable (`chmod +x`)
- Must work on macOS and Linux
- Must include usage/help when called with `-h` or `--help`
- Log output to stdout with timestamps

## 4. Testing Strategy

Since these are shell scripts, tests will be Python-based using subprocess:

### `tests/test_launch_scripts.py`

1. **test_launch_script_exists** -- `scripts/launch_agents.sh` exists and is executable
2. **test_stop_script_exists** -- `scripts/stop_agents.sh` exists and is executable
3. **test_launch_script_has_shebang** -- First line is `#!/usr/bin/env bash`
4. **test_stop_script_has_shebang** -- First line is `#!/usr/bin/env bash`
5. **test_launch_script_has_set_flags** -- Contains `set -euo pipefail`
6. **test_stop_script_has_set_flags** -- Contains `set -euo pipefail`
7. **test_launch_script_defines_all_agents** -- Contains port mappings for 8000-8007
8. **test_launch_script_creates_pid_dir** -- References `.pids/` directory creation
9. **test_launch_script_has_health_check** -- Contains curl health check logic
10. **test_stop_script_handles_missing_pids_dir** -- Handles case when `.pids/` doesn't exist
11. **test_stop_script_sends_sigterm** -- Contains SIGTERM logic
12. **test_stop_script_has_force_flag** -- Contains `--force` flag handling
13. **test_launch_script_help_flag** -- Running with `-h` exits 0 and shows usage
14. **test_stop_script_help_flag** -- Running with `-h` exits 0 and shows usage
15. **test_launch_script_has_no_health_check_flag** -- Contains `--no-health-check` flag

## 5. Acceptance Criteria

- [ ] `scripts/launch_agents.sh` exists, is executable, and defines all 8 agents
- [ ] `scripts/stop_agents.sh` exists, is executable, with SIGTERM/SIGKILL logic
- [ ] PID management via `.pids/` directory
- [ ] Health check after launch (with `--no-health-check` skip option)
- [ ] Both scripts have proper shebang, `set -euo pipefail`, and help flags
- [ ] Both scripts handle edge cases gracefully (missing dirs, stale PIDs)
- [ ] All 15 tests pass
- [ ] Scripts pass shellcheck (if available) or follow bash best practices
- [ ] `.pids/` added to `.gitignore`

## 6. Out of Scope

- Actually running agents (agents may not exist yet)
- Docker integration (handled by S11.1/S11.2)
- Systemd/launchd service files
- Log rotation or log file management
