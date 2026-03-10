# Spec S11.5 -- Health Check Script

## Meta
| Field | Value |
|-------|-------|
| Spec ID | S11.5 |
| Title | Health Check Script |
| Phase | 11 -- Infrastructure |
| Depends on | S11.3 (Launch Scripts) |
| Produces | `scripts/health_check.sh` |
| Status | spec-written |

## 1. Purpose

Provide a standalone health check script that curls each agent's `/health` endpoint and reports a status table. Used by operators, CI, Docker HEALTHCHECK, and the launch scripts to verify all agents are running.

## 2. Background

S11.3 launch scripts include an inline health check after launch. This spec extracts a dedicated, reusable `health_check.sh` that can be called independently -- from Docker HEALTHCHECK, monitoring cron jobs, or manual checks. It checks all 8 agents (MarketConductor on 8000 + 7 specialists on 8001-8007) and exits with code 1 if any agent is down.

## 3. Deliverables

### 3.1 `scripts/health_check.sh`

Bash script that:
1. Curls each agent's `/health` endpoint with a configurable timeout
2. Reports a status table with agent name, port, and status (UP/DOWN)
3. Exits with code 0 if all agents are healthy, 1 if any are down
4. Supports `--port PORT` to check a single agent
5. Supports `--timeout SECONDS` to override default curl timeout (default: 2s)
6. Supports `-h` / `--help` for usage information
7. Supports `--json` flag for machine-readable JSON output

**Agent mapping (same as S11.3):**
| Agent | Port |
|-------|------|
| market_conductor | 8000 |
| valuation_scout | 8001 |
| momentum_tracker | 8002 |
| pulse_monitor | 8003 |
| economy_watcher | 8004 |
| compliance_checker | 8005 |
| signal_synthesizer | 8006 |
| risk_guardian | 8007 |

**Script behavior:**
- Uses `curl -sf --max-time {timeout} http://localhost:{port}/health`
- Color-coded output: green for UP, red for DOWN (only when stdout is a terminal)
- Summary line at the end: "X/8 agents healthy"
- Must have `#!/usr/bin/env bash` shebang
- Must use `set -euo pipefail`
- Must be executable (`chmod +x`)
- Must work on macOS and Linux
- Log output to stdout with timestamps

### 3.2 Single-Port Mode

When `--port PORT` is specified:
- Only check that one port
- Print single-line result (agent name, port, status)
- Exit 0 if healthy, 1 if down
- Useful for Docker HEALTHCHECK on a specific agent

### 3.3 JSON Output Mode

When `--json` is specified:
- Output a JSON object with `agents` array and `summary` object
- Each agent entry: `{"name": "...", "port": N, "status": "UP"|"DOWN"}`
- Summary: `{"healthy": N, "total": N, "all_healthy": true|false}`
- No color codes in JSON mode

---

## Functional Requirements

### FR-1: Health Check All Agents
- **What**: Curl each of the 8 agent `/health` endpoints and report status
- **Inputs**: None (uses hardcoded agent list matching S11.3)
- **Outputs**: Status table to stdout, exit code 0 (all UP) or 1 (any DOWN)
- **Edge cases**: Agent not responding (timeout), connection refused

### FR-2: Single-Port Check
- **What**: Check a single agent by port number
- **Inputs**: `--port PORT` argument
- **Outputs**: Single-line status, appropriate exit code
- **Edge cases**: Unknown port (not in 8000-8007 range -- still check it), invalid port value

### FR-3: Configurable Timeout
- **What**: Allow overriding the default 2-second curl timeout
- **Inputs**: `--timeout SECONDS` argument
- **Outputs**: Uses specified timeout for curl calls
- **Edge cases**: Non-numeric timeout value

### FR-4: JSON Output
- **What**: Machine-readable JSON output for scripting/monitoring
- **Inputs**: `--json` flag
- **Outputs**: JSON object with agents array and summary
- **Edge cases**: Combine with `--port` for single-agent JSON

### FR-5: Help Flag
- **What**: Show usage information
- **Inputs**: `-h` or `--help`
- **Outputs**: Usage text, exit 0

---

## Tangible Outcomes

- [ ] **Outcome 1**: `scripts/health_check.sh` exists and is executable
- [ ] **Outcome 2**: Running with `-h` prints usage and exits 0
- [ ] **Outcome 3**: Script defines all 8 agents on ports 8000-8007
- [ ] **Outcome 4**: Script uses curl with configurable timeout to check `/health`
- [ ] **Outcome 5**: Script outputs a formatted status table with agent name, port, status
- [ ] **Outcome 6**: Script supports `--port`, `--timeout`, `--json` flags
- [ ] **Outcome 7**: Script exits 1 if any agent is down, 0 if all healthy
- [ ] **Outcome 8**: All tests pass

---

## Test-Driven Requirements

### Tests to Write First (Red -> Green)

File: `tests/test_health_check_script.py`

1. **test_health_check_script_exists** -- `scripts/health_check.sh` exists
2. **test_health_check_script_is_executable** -- File has executable permission
3. **test_health_check_script_has_shebang** -- First line is `#!/usr/bin/env bash`
4. **test_health_check_script_has_set_flags** -- Contains `set -euo pipefail`
5. **test_health_check_script_defines_all_agents** -- Contains port mappings for 8000-8007
6. **test_health_check_script_has_curl_health** -- Contains curl to `/health` endpoint
7. **test_health_check_script_has_timeout_flag** -- Contains `--timeout` flag handling
8. **test_health_check_script_has_port_flag** -- Contains `--port` flag handling
9. **test_health_check_script_has_json_flag** -- Contains `--json` flag handling
10. **test_health_check_script_help_flag** -- Running with `-h` exits 0 and shows usage
11. **test_health_check_script_has_summary_line** -- Contains summary output logic
12. **test_health_check_script_has_color_codes** -- Contains GREEN/RED color definitions
13. **test_health_check_script_exit_code_logic** -- Contains exit 1 logic for failures

### Mocking Strategy
- Tests are static analysis of the shell script content + subprocess for `-h` flag
- No actual agents need to be running

### Coverage Expectation
- All flags and features have at least one test
- Script structure validated via content inspection

---

## References
- `roadmap.md` -- S11.5 spec definition
- `specs/spec-S11.3-launch-scripts/spec.md` -- Agent port mapping, health check pattern
- `scripts/launch_agents.sh` -- Inline health check to extract and extend
