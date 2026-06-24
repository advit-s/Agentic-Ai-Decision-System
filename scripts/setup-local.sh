#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# setup-local.sh — One-command local setup for the Agentic Decision System
#
# Usage:
#   ./scripts/setup-local.sh            # Normal setup
#   ./scripts/setup-local.sh --force    # Overwrite .env from .env.example
#
# This script:
#   1. Checks required tools (python, node, npm)
#   2. Creates .env from .env.example if missing (or --force)
#   3. Creates Python virtual environment
#   4. Installs backend with dev/doc-parsing/ocr extras
#   5. Installs frontend dependencies
#   6. Creates .decision_system data directory
#   7. Prints next steps
#
# Does NOT overwrite user data or existing .env unless --force is used.
# Repeatable: safe to run multiple times.
# ---------------------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

FORCE="${1:-}"

PASS=0
FAIL=0
INFO=0

pass() { PASS=$((PASS+1)); echo "  ✅ $1"; }
fail() { FAIL=$((FAIL+1)); echo "  ❌ $1"; }
info() { INFO=$((INFO+1)); echo "  ℹ️  $1"; }

echo "============================================"
echo "  Agentic Decision System — Local Setup"
echo "  Version: $(python3 -c "import sys; sys.path.insert(0,'src'); exec(open('src/decision_system/__init__').read()); print(__version__)" 2>/dev/null || echo "unknown")"
echo "============================================"
echo ""

# ------------------------------------------------------------------
# 1. Check Python version
# ------------------------------------------------------------------
echo "--- [1/7] Checking Python ---"
if command -v python3 &>/dev/null; then
    PY=$(python3 --version 2>&1)
    pass "Python found: $PY"
    # Check >= 3.11
    PY_MAJOR=$(python3 -c "import sys; print(sys.version_info.major)")
    PY_MINOR=$(python3 -c "import sys; print(sys.version_info.minor)")
    if [ "$PY_MAJOR" -lt 3 ] || ([ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 11 ]); then
        fail "Python 3.11+ required (found $PY_MAJOR.$PY_MINOR)"
    else
        pass "Python version OK (3.11+)"
    fi
else
    fail "python3 not found. Install Python 3.11+ first."
fi

# ------------------------------------------------------------------
# 2. Check Node.js version
# ------------------------------------------------------------------
echo "--- [2/7] Checking Node.js ---"
if command -v node &>/dev/null; then
    NODE_VER=$(node --version 2>&1)
    pass "Node found: $NODE_VER"
    if command -v npm &>/dev/null; then
        NPM_VER=$(npm --version 2>&1)
        pass "npm found: $NPM_VER"
    else
        fail "npm not found. Install npm first."
    fi
else
    fail "node not found. Install Node.js 18+ first."
fi

# ------------------------------------------------------------------
# 3. Create .env from .env.example
# ------------------------------------------------------------------
echo "--- [3/7] Setting up environment ---"
if [ ! -f ".env" ]; then
    cp .env.example .env
    pass "Created .env from .env.example"
elif [ "$FORCE" = "--force" ]; then
    cp .env.example .env
    pass "Overwrote .env from .env.example (--force)"
else
    info ".env already exists (not overwriting). Use --force to reset."
fi

# ------------------------------------------------------------------
# 4. Create Python virtual environment and install backend
# ------------------------------------------------------------------
echo "--- [4/7] Setting up Python virtual environment ---"
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    pass "Created .venv virtual environment"
else
    info ".venv already exists"
fi

echo "--- [5/7] Installing backend dependencies ---"
.venv/bin/python -m pip install -e ".[dev,doc-parsing,ocr]" 2>&1 | tail -3
if [ $? -eq 0 ]; then
    pass "Backend dependencies installed"
else
    fail "Backend dependency installation failed"
fi

# ------------------------------------------------------------------
# 6. Install frontend dependencies
# ------------------------------------------------------------------
echo "--- [6/7] Installing frontend dependencies ---"
if [ -d "web/workflow-builder/node_modules" ]; then
    info "node_modules exists, running npm install to ensure up-to-date"
fi

(cd web/workflow-builder && npm install 2>&1 | tail -3)
if [ $? -eq 0 ]; then
    pass "Frontend dependencies installed"
else
    fail "Frontend dependency installation failed"
fi

# ------------------------------------------------------------------
# 7. Create data directory
# ------------------------------------------------------------------
echo "--- [7/7] Creating data directory ---"
mkdir -p .decision_system
pass "Created .decision_system/ data directory"

# ------------------------------------------------------------------
# Summary
# ------------------------------------------------------------------
echo ""
echo "============================================"
echo "  Setup complete!"
echo "  Passed: $PASS   Failed: $FAIL   Info: $INFO"
echo "============================================"
echo ""

if [ "$FAIL" -gt 0 ]; then
    echo "Some steps failed. Fix the issues above and re-run."
    exit 1
fi

echo "Next steps:"
echo ""
echo "  # Start the backend API:"
echo "  .venv/bin/decision-system serve-api --host 0.0.0.0 --port 8000"
echo ""
echo "  # Or start everything (backend + frontend):"
echo "  ./scripts/start-local.sh"
echo ""
echo "  # Open the app:"
echo "  http://localhost:8000"
echo "  http://localhost:5173 (frontend dev server)"
echo ""
echo "  # Run diagnostics:"
echo "  ./scripts/doctor-local.sh"
echo ""
echo "  # Run the demo seed:"
echo "  bash scripts/local-demo-seed.sh"
echo ""
echo "  # Validate the install:"
echo "  ./scripts/validate-local.sh"
echo ""
echo "  # Read docs:"
echo "  cat docs/LOCAL_FIRST_SETUP.md"
echo "  cat docs/DEMO_PATH.md"
echo ""
