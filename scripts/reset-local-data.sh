#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# reset-local-data.sh — Safely reset all local data
#
# Deletes .decision_system/ directory after confirmation prompt.
# Does NOT delete source code, .env, or configuration.
#
# Usage:
#   ./scripts/reset-local-data.sh           # Prompt for confirmation
#   ./scripts/reset-local-data.sh --yes      # Skip confirmation
#
# After reset, re-run:
#   ./scripts/setup-local.sh
#   ./scripts/local-demo-seed.sh
# ---------------------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

AUTO_YES=false
if [ "${1:-}" = "--yes" ]; then
    AUTO_YES=true
fi

echo "============================================"
echo "  Reset Local Data — Agentic Decision System"
echo "============================================"
echo ""
echo "  This will DELETE all local data:"
echo ""
echo "  - .decision_system/"
echo "    ├── chroma/        (vector store)"
echo "    ├── workspaces/    (workspace metadata)"
echo "    ├── providers/     (provider configs)"
echo "    ├── data_sources/  (uploaded files)"
echo "    ├── reports/       (generated reports)"
echo "    ├── connectors/    (imported connector data)"
echo "    ├── logs/          (application logs)"
echo "    └── pids/          (process ID files)"
echo ""
echo "  Your source code and configuration will NOT be affected."
echo "  Your .env file will NOT be deleted."
echo ""

if [ "$AUTO_YES" = false ]; then
    echo -n "  Are you sure? Type 'yes' to continue: "
    read -r CONFIRM
    if [ "$CONFIRM" != "yes" ]; then
        echo ""
        echo "  Reset cancelled."
        exit 0
    fi
fi

if [ -d ".decision_system" ]; then
    echo ""
    echo "  Deleting .decision_system/..."
    rm -rf .decision_system/
    echo "  ✅ Data deleted."
else
    echo "  No .decision_system/ directory found. Nothing to reset."
fi

echo ""
echo "  === Next steps ==="
echo ""
echo "  1. Run setup:    ./scripts/setup-local.sh"
echo "  2. Start API:    ./scripts/start-local.sh"
echo "  3. Seed demo:    bash scripts/local-demo-seed.sh"
echo "  4. Open app:     http://localhost:8000"
echo ""
