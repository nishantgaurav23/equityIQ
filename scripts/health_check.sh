#!/usr/bin/env bash
set -euo pipefail

# EquityIQ -- Health check for all agents
# Usage: ./scripts/health_check.sh [--port PORT] [--timeout SECONDS] [--json] [-h|--help]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Agent definitions: name:port
AGENTS=(
    "market_conductor:8000"
    "valuation_scout:8001"
    "momentum_tracker:8002"
    "pulse_monitor:8003"
    "economy_watcher:8004"
    "compliance_checker:8005"
    "signal_synthesizer:8006"
    "risk_guardian:8007"
)

# Colors (only used when stdout is a terminal)
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

if [ ! -t 1 ]; then
    GREEN=''
    RED=''
    NC=''
fi

# Defaults
TIMEOUT=2
CHECK_PORT=""
JSON_OUTPUT=false

usage() {
    echo "Usage: $(basename "$0") [OPTIONS]"
    echo ""
    echo "Check health of all EquityIQ agents."
    echo ""
    echo "Options:"
    echo "  --port PORT         Check a single agent by port number"
    echo "  --timeout SECONDS   Curl timeout in seconds (default: 2)"
    echo "  --json              Output results as JSON"
    echo "  -h, --help          Show this help message"
    echo ""
    echo "Agents:"
    echo "  market_conductor    port 8000"
    echo "  valuation_scout     port 8001"
    echo "  momentum_tracker    port 8002"
    echo "  pulse_monitor       port 8003"
    echo "  economy_watcher     port 8004"
    echo "  compliance_checker  port 8005"
    echo "  signal_synthesizer  port 8006"
    echo "  risk_guardian       port 8007"
    echo ""
    echo "Exit codes:"
    echo "  0  All checked agents are healthy"
    echo "  1  One or more agents are down"
}

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --port)
            CHECK_PORT="$2"
            shift 2
            ;;
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        --json)
            JSON_OUTPUT=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Resolve agent name from port
get_agent_name() {
    local port="$1"
    for agent_def in "${AGENTS[@]}"; do
        IFS=':' read -r name aport <<< "$agent_def"
        if [ "$aport" = "$port" ]; then
            echo "$name"
            return
        fi
    done
    echo "unknown"
}

# Check a single agent's health
check_agent() {
    local name="$1"
    local port="$2"
    if curl -sf --max-time "$TIMEOUT" "http://localhost:${port}/health" > /dev/null 2>&1; then
        echo "UP"
    else
        echo "DOWN"
    fi
}

# Build list of agents to check
if [ -n "$CHECK_PORT" ]; then
    AGENT_NAME=$(get_agent_name "$CHECK_PORT")
    CHECK_LIST=("${AGENT_NAME}:${CHECK_PORT}")
else
    CHECK_LIST=("${AGENTS[@]}")
fi

TOTAL=${#CHECK_LIST[@]}
HEALTHY=0
FAILED=0

# JSON mode
if [ "$JSON_OUTPUT" = true ]; then
    JSON_AGENTS="["
    FIRST=true

    for agent_def in "${CHECK_LIST[@]}"; do
        IFS=':' read -r name port <<< "$agent_def"
        status=$(check_agent "$name" "$port")

        if [ "$status" = "UP" ]; then
            HEALTHY=$((HEALTHY + 1))
        else
            FAILED=$((FAILED + 1))
        fi

        if [ "$FIRST" = true ]; then
            FIRST=false
        else
            JSON_AGENTS+=","
        fi
        JSON_AGENTS+="{\"name\":\"${name}\",\"port\":${port},\"status\":\"${status}\"}"
    done

    JSON_AGENTS+="]"

    ALL_HEALTHY=false
    if [ "$FAILED" -eq 0 ]; then
        ALL_HEALTHY=true
    fi

    echo "{\"agents\":${JSON_AGENTS},\"summary\":{\"healthy\":${HEALTHY},\"total\":${TOTAL},\"all_healthy\":${ALL_HEALTHY}}}"

    if [ "$FAILED" -gt 0 ]; then
        exit 1
    fi
    exit 0
fi

# Table mode
log "Checking EquityIQ agent health..."
echo ""

printf "%-25s %-6s %-8s\n" "AGENT" "PORT" "STATUS"
printf "%-25s %-6s %-8s\n" "-----" "----" "------"

for agent_def in "${CHECK_LIST[@]}"; do
    IFS=':' read -r name port <<< "$agent_def"
    status=$(check_agent "$name" "$port")

    if [ "$status" = "UP" ]; then
        HEALTHY=$((HEALTHY + 1))
        printf "%-25s %-6s ${GREEN}%-8s${NC}\n" "$name" "$port" "UP"
    else
        FAILED=$((FAILED + 1))
        printf "%-25s %-6s ${RED}%-8s${NC}\n" "$name" "$port" "DOWN"
    fi
done

echo ""
log "${HEALTHY}/${TOTAL} agents healthy"

if [ "$FAILED" -gt 0 ]; then
    log "${RED}${FAILED} agent(s) are down.${NC}"
    exit 1
else
    log "${GREEN}All agents healthy.${NC}"
fi

exit 0
