#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# start-local.sh — Start the local backend API and optionally the frontend
#
# Usage:
#   ./scripts/start-local.sh            # Start backend only
#   ./scripts/start-local.sh --all      # Start backend + frontend dev server
#   ./scripts/start-local.sh --backend  # Start backend only (default)
#   ./scripts/start-local.sh --frontend # Start frontend dev server only
#
# Logs:
#   .decision_system/logs/backend.log
#   .decision_system/logs/frontend.log
#
# Stop with:
#   ./scripts/stop-local.sh
#   Or Ctrl+C in this terminal
# ---------------------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

MODE="${1:-backend}"

# Detect Python
if [ -f ".venv/bin/python" ]; then
    PYTHON=".venv/bin/python"
else
    PYTHON="python3"
fi

mkdir -p .decision_system/logs

echo "============================================"
echo "  Agentic Decision System — Local Start"
echo "============================================"

case "$MODE" in
    --all|-a)
        echo "Starting backend + frontend..."
        echo ""
        echo "  Backend:  http://localhost:8000"
        echo "  Frontend: http://localhost:5173"
        echo "  API docs: http://localhost:8000/docs"
        echo ""
        echo "  Logs:"
        echo "    .decision_system/logs/backend.log"
        echo "    .decision_system/logs/frontend.log"
        echo ""
        echo "  Stop with:  ./scripts/stop-local.sh"
        echo ""

        # Start backend in background
        $PYTHON -m decision_system.cli serve-api --host 0.0.0.0 --port 8000 \
            > .decision_system/logs/backend.log 2>&1 &
        BACKEND_PID=$!
        echo "  Backend PID: $BACKEND_PID"

        # Start frontend in background
        (cd web/workflow-builder && npm run dev \
            > "$PROJECT_DIR/.decision_system/logs/frontend.log" 2>&1) &
        FRONTEND_PID=$!
        echo "  Frontend PID: $FRONTEND_PID"

        echo ""
        echo "  Waiting for backend health..."
        for i in $(seq 1 30); do
            if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
                echo "  ✅ Backend ready"
                break
            fi
            sleep 1
        done

        echo ""
        echo "  Running. PIDs saved to .decision_system/pids"

        # Save PIDs for stop script
        echo "$BACKEND_PID" > .decision_system/pids/backend.pid 2>/dev/null || true
        echo "$FRONTEND_PID" > .decision_system/pids/frontend.pid 2>/dev/null || true
        mkdir -p .decision_system/pids
        echo "$BACKEND_PID" > .decision_system/pids/backend.pid
        echo "$FRONTEND_PID" > .decision_system/pids/frontend.pid

        echo ""
        echo "  Press Ctrl+C to stop both services."
        wait
        ;;

    --frontend|-f)
        echo "Starting frontend dev server..."
        echo "  http://localhost:5173"
        (cd web/workflow-builder && npm run dev)
        ;;

    --backend|-b|*)
        echo "Starting backend API..."
        echo "  http://localhost:8000"
        echo "  http://localhost:8000/docs"
        echo "  http://localhost:8000/health"
        echo ""
        echo "  Stop with: Ctrl+C"
        echo ""
        exec $PYTHON -m decision_system.cli serve-api --host 0.0.0.0 --port 8000
        ;;
esac
