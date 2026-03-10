#!/usr/bin/env bash
set -euo pipefail

# EquityIQ -- Stop all running agents
# Usage: ./scripts/stop_agents.sh [--force] [-h|--help]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PID_DIR="$PROJECT_ROOT/.pids"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Flags
FORCE=false

usage() {
    echo "Usage: $(basename "$0") [OPTIONS]"
    echo ""
    echo "Stop all running EquityIQ agents."
    echo ""
    echo "Options:"
    echo "  --force    Skip SIGTERM, send SIGKILL immediately"
    echo "  -h, --help Show this help message"
}

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

# Parse arguments
for arg in "$@"; do
    case "$arg" in
        --force)
            FORCE=true
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

# Check if .pids/ directory exists
if [ ! -d "$PID_DIR" ]; then
    log "No .pids/ directory found. No agents are running."
    exit 0
fi

# Check if there are any PID files
shopt -s nullglob
pid_files=("$PID_DIR"/*.pid)
shopt -u nullglob

if [ ${#pid_files[@]} -eq 0 ]; then
    log "No PID files found in .pids/. No agents are running."
    exit 0
fi

log "Stopping EquityIQ agents..."
echo ""

printf "%-25s %-8s %-8s\n" "AGENT" "PID" "STATUS"
printf "%-25s %-8s %-8s\n" "-----" "---" "------"

for pid_file in "${pid_files[@]}"; do
    name=$(basename "$pid_file" .pid)
    pid=$(cat "$pid_file")

    # Check if process is still running
    if ! kill -0 "$pid" 2>/dev/null; then
        printf "%-25s %-8s ${YELLOW}%-8s${NC}\n" "$name" "$pid" "ALREADY DEAD"
        rm -f "$pid_file"
        continue
    fi

    if [ "$FORCE" = true ]; then
        # Force kill immediately with SIGKILL
        kill -9 "$pid" 2>/dev/null || true
        printf "%-25s %-8s ${RED}%-8s${NC}\n" "$name" "$pid" "KILLED"
    else
        # Send SIGTERM first
        kill "$pid" 2>/dev/null || true

        # Wait up to 5 seconds for graceful shutdown
        waited=0
        while kill -0 "$pid" 2>/dev/null && [ $waited -lt 5 ]; do
            sleep 1
            waited=$((waited + 1))
        done

        if kill -0 "$pid" 2>/dev/null; then
            # Still running after 5s, send SIGKILL
            kill -9 "$pid" 2>/dev/null || true
            printf "%-25s %-8s ${RED}%-8s${NC}\n" "$name" "$pid" "FORCE KILLED"
        else
            printf "%-25s %-8s ${GREEN}%-8s${NC}\n" "$name" "$pid" "STOPPED"
        fi
    fi

    rm -f "$pid_file"
done

# Clean up .pids/ directory if empty
shopt -s nullglob
remaining=("$PID_DIR"/*)
shopt -u nullglob

if [ ${#remaining[@]} -eq 0 ]; then
    rmdir "$PID_DIR" 2>/dev/null || true
    log "Cleaned up .pids/ directory."
fi

echo ""
log "All agents stopped."
exit 0
