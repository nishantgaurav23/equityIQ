#!/usr/bin/env bash
set -euo pipefail

# EquityIQ -- Launch all agents on designated ports
# Usage: ./scripts/launch_agents.sh [--no-health-check] [-h|--help]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PID_DIR="$PROJECT_ROOT/.pids"

# Agent definitions: name:module:port
AGENTS=(
    "market_conductor:agents.market_conductor:8000"
    "valuation_scout:agents.valuation_scout:8001"
    "momentum_tracker:agents.momentum_tracker:8002"
    "pulse_monitor:agents.pulse_monitor:8003"
    "economy_watcher:agents.economy_watcher:8004"
    "compliance_checker:agents.compliance_checker:8005"
    "signal_synthesizer:agents.signal_synthesizer:8006"
    "risk_guardian:agents.risk_guardian:8007"
)

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Flags
SKIP_HEALTH_CHECK=false

usage() {
    echo "Usage: $(basename "$0") [OPTIONS]"
    echo ""
    echo "Launch all EquityIQ agents on ports 8000-8007."
    echo ""
    echo "Options:"
    echo "  --no-health-check   Skip health check after launch"
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
}

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

# Parse arguments
for arg in "$@"; do
    case "$arg" in
        --no-health-check)
            SKIP_HEALTH_CHECK=true
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $arg"
            usage
            exit 1
            ;;
    esac
done

# Create PID directory
mkdir -p "$PID_DIR"

log "Starting EquityIQ agents..."
echo ""

FAILED=0

for agent_def in "${AGENTS[@]}"; do
    IFS=':' read -r name module port <<< "$agent_def"

    log "Starting $name on port $port..."
    uvicorn "$module:app" --host 0.0.0.0 --port "$port" &
    pid=$!
    echo "$pid" > "$PID_DIR/${name}.pid"
    log "  PID: $pid -> $PID_DIR/${name}.pid"
done

echo ""

# Health check
if [ "$SKIP_HEALTH_CHECK" = false ]; then
    log "Waiting 2 seconds for agents to start..."
    sleep 2

    echo ""
    printf "%-25s %-6s %-8s %-8s\n" "AGENT" "PORT" "PID" "STATUS"
    printf "%-25s %-6s %-8s %-8s\n" "-----" "----" "---" "------"

    for agent_def in "${AGENTS[@]}"; do
        IFS=':' read -r name module port <<< "$agent_def"
        pid_file="$PID_DIR/${name}.pid"

        if [ -f "$pid_file" ]; then
            pid=$(cat "$pid_file")
            if curl -sf --max-time 2 "http://localhost:${port}/health" > /dev/null 2>&1; then
                printf "%-25s %-6s %-8s ${GREEN}%-8s${NC}\n" "$name" "$port" "$pid" "UP"
            else
                printf "%-25s %-6s %-8s ${RED}%-8s${NC}\n" "$name" "$port" "$pid" "DOWN"
                FAILED=$((FAILED + 1))
            fi
        else
            printf "%-25s %-6s %-8s ${RED}%-8s${NC}\n" "$name" "$port" "N/A" "NO PID"
            FAILED=$((FAILED + 1))
        fi
    done

    echo ""
    if [ "$FAILED" -gt 0 ]; then
        log "${RED}$FAILED agent(s) failed to start.${NC}"
        exit 1
    else
        log "${GREEN}All agents started successfully.${NC}"
    fi
else
    log "Health check skipped (--no-health-check)."
fi

exit 0
