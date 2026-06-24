#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# stop-local.sh — Stop local backend and frontend processes
#
# Usage:
#   ./scripts/stop-local.sh             # Stop all local processes
#   ./scripts/stop-local.sh --backend   # Stop backend only
#   ./scripts/stop-local.sh --frontend  # Stop frontend only
#
# Uses saved PIDs from .decision_system/pids/ if available.
# Falls back to pkill/pgrep if PID files are missing.
# ---------------------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

MODE="${1:-all}"

PID_DIR=".decision_system/pids"

stop_process() {
    local name="$1"
    local pid_file="$2"
    local process_pattern="$3"

    if [ -f "$pid_file" ]; then
        local PID
        PID=$(cat "$pid_file" 2>/dev/null || echo "")
        if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
            echo "  Stopping $name (PID $PID)..."
            kill "$PID" 2>/dev/null || true
            sleep 1
            if kill -0 "$PID" 2>/dev/null; then
                kill -9 "$PID" 2>/dev/null || true
                echo "  $name force-killed"
            else
                echo "  $name stopped"
            fi
        else
            echo "  $name not running (stale PID)"
        fi
        rm -f "$pid_file"
    else
        # Fallback: try pkill
        if command -v pkill &>/dev/null; then
            if pkill -f "$process_pattern" 2>/dev/null; then
                echo "  $name stopped (via pkill)"
            else
                echo "  $name not running"
            fi
        else
            echo "  $name not running (no PID file found)"
        fi
    fi
}

echo "============================================"
echo "  Agentic Decision System — Local Stop"
echo "============================================"
echo ""

mkdir -p "$PID_DIR"

case "$MODE" in
    --backend|-b)
        stop_process "backend" "$PID_DIR/backend.pid" "decision_system.cli serve-api"
        ;;
    --frontend|-f)
        stop_process "frontend" "$PID_DIR/frontend.pid" "web/workflow-builder.*vite"
        ;;
    --all|-a|*)
        stop_process "frontend" "$PID_DIR/frontend.pid" "web/workflow-builder.*vite"
        stop_process "backend" "$PID_DIR/backend.pid" "decision_system.cli serve-api"
        ;;
esac

echo ""
echo "Done."
