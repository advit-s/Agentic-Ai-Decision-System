#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# doctor-local.sh — Local installation diagnostics
#
# Checks:
#   Python version, Node version, Docker availability
#   Backend health (if running)
#   Frontend health (if running)
#   Data directory existence
#   .env existence
#   OCR availability
#   Doc parser dependencies importable
#   Frontend build artifacts
#
# Usage:
#   ./scripts/doctor-local.sh           # Run all checks
#   ./scripts/doctor-local.sh --quiet   # Less verbose output
#
# No cloud API keys required.
# ---------------------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

QUIET=false
if [ "${1:-}" = "--quiet" ]; then
    QUIET=true
fi

PASS=0
WARN=0
FAIL=0

pass() { PASS=$((PASS+1)); $QUIET || echo "  ✅ $1"; }
warn() { WARN=$((WARN+1)); echo "  ⚠️  $1"; }
fail() { FAIL=$((FAIL+1)); echo "  ❌ $1"; }

echo "============================================"
echo "  Agentic Decision System — Doctor"
echo "============================================"
echo ""

# --- 1. Python ---
echo "--- Python ---"
if command -v python3 &>/dev/null; then
    VER=$(python3 --version 2>&1)
    PY_MAJOR=$(python3 -c "import sys; print(sys.version_info.major)")
    PY_MINOR=$(python3 -c "import sys; print(sys.version_info.minor)")
    if [ "$PY_MAJOR" -ge 3 ] && [ "$PY_MINOR" -ge 11 ]; then
        pass "Python $VER OK"
    else
        warn "Python $VER — 3.11+ recommended"
    fi
else
    fail "python3 not found"
fi

# --- 2. Node ---
echo "--- Node.js ---"
if command -v node &>/dev/null; then
    NODE_VER=$(node --version 2>&1)
    NODE_MAJOR=$(node -e "console.log(process.version.slice(1).split('.')[0])")
    if [ "$NODE_MAJOR" -ge 18 ]; then
        pass "Node $NODE_VER OK"
    else
        warn "Node $NODE_VER — 18+ recommended"
    fi
    if command -v npm &>/dev/null; then
        pass "npm $(npm --version) OK"
    else
        fail "npm not found"
    fi
else
    fail "node not found"
fi

# --- 3. Docker ---
echo "--- Docker ---"
if command -v docker &>/dev/null; then
    DOCKER_VER=$(docker --version 2>&1)
    pass "Docker available: $DOCKER_VER"
    if docker compose version &>/dev/null 2>&1; then
        pass "Docker Compose available"
    else
        warn "Docker Compose not available (legacy docker-compose?)"
    fi
else
    warn "Docker not found (optional for containerized setup)"
fi

# --- 4. Backend health ---
echo "--- Backend ---"
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
if HEALTH=$(curl -sf "$BACKEND_URL/health" 2>/dev/null); then
    VERSION=$(echo "$HEALTH" | python3 -c "import sys,json; print(json.load(sys.stdin).get('version','?'))" 2>/dev/null || echo "?")
    pass "Backend reachable at $BACKEND_URL (version $VERSION)"
else
    warn "Backend not running at $BACKEND_URL (start with ./scripts/start-local.sh)"
fi

# --- 5. Frontend health ---
echo "--- Frontend ---"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:5173}"
if curl -sf -o /dev/null "$FRONTEND_URL" 2>/dev/null; then
    pass "Frontend reachable at $FRONTEND_URL"
else
    FRONTEND_URL2="http://localhost:3000"
    if curl -sf -o /dev/null "$FRONTEND_URL2" 2>/dev/null; then
        pass "Frontend reachable at $FRONTEND_URL2"
    else
        warn "Frontend not running (start with ./scripts/start-local.sh --all)"
    fi
fi

# --- 6. Data directory ---
echo "--- Data Directory ---"
if [ -d ".decision_system" ]; then
    SIZE=$(du -sh .decision_system 2>/dev/null | cut -f1)
    pass ".decision_system/ exists ($SIZE)"
else
    warn ".decision_system/ does not exist (run setup first)"
fi

# --- 7. .env ---
echo "--- Environment ---"
if [ -f ".env" ]; then
    HAS_PROVIDER=$(grep -c "^DECISION_PROVIDER=" .env 2>/dev/null || echo 0)
    if [ "$HAS_PROVIDER" -gt 0 ]; then
        pass ".env exists with DECISION_PROVIDER set"
    else
        warn ".env exists but may be incomplete"
    fi
else
    warn ".env not found (cp .env.example .env)"
fi

# --- 8. OCR availability ---
echo "--- OCR ---"
if command -v tesseract &>/dev/null; then
    TESS_VER=$(tesseract --version 2>&1 | head -1)
    pass "Tesseract installed: $TESS_VER"
    # Check tessdata
    TESSDATA="${TESSDATA_PREFIX:-}"
    if [ -z "$TESSDATA" ]; then
        for DIR in /usr/share/tesseract-ocr/5/tessdata /usr/share/tesseract-ocr/4.00/tessdata /usr/local/share/tessdata; do
            if [ -f "$DIR/eng.traineddata" ]; then
                TESSDATA="$DIR"
                break
            fi
        done
    fi
    if [ -n "$TESSDATA" ] && [ -f "$TESSDATA/eng.traineddata" ]; then
        pass "Tessdata found: $TESSDATA"
    else
        warn "Tessdata not found (OCR may fail)"
    fi
else
    warn "Tesseract not installed (OCR unavailable)"
fi

# Python OCR deps
if python3 -c "import tesserocr" 2>/dev/null; then
    pass "tesserocr importable"
else
    warn "tesserocr not installable (pip install -e '.[ocr]')"
fi

# --- 9. Doc parser dependencies ---
echo "--- Document Parsing ---"
if python3 -c "import pypdf" 2>/dev/null; then
    pass "pypdf importable"
else
    warn "pypdf not installable (pip install -e '.[doc-parsing]')"
fi
if python3 -c "import docx" 2>/dev/null; then
    pass "python-docx importable"
else
    warn "python-docx not installable"
fi
if python3 -c "import openpyxl" 2>/dev/null; then
    pass "openpyxl importable"
else
    warn "openpyxl not installable"
fi

# --- 10. Frontend build ---
echo "--- Frontend Build ---"
if [ -f "web/workflow-builder/dist/index.html" ]; then
    pass "Frontend build exists (web/workflow-builder/dist/)"
else
    warn "Frontend build not found (run 'cd web/workflow-builder && npm run build')"
fi
if .venv/bin/python -c "from decision_system import __version__; print(__version__)" 2>/dev/null; then
    VER=$(.venv/bin/python -c "from decision_system import __version__; print(__version__)" 2>/dev/null)
    pass "Backend package importable (version $VER)"
else
    fail "Backend package not importable"
fi

# --- Summary ---
echo ""
echo "============================================"
echo "  Doctor Results: $PASS passed, $WARN warnings, $FAIL failed"
echo "============================================"
echo ""
if [ "$FAIL" -gt 0 ]; then
    echo "Fix failures before proceeding. Warnings are informational."
    exit 1
elif [ "$WARN" -gt 0 ]; then
    echo "All critical checks passed. Review warnings for optional improvements."
    exit 0
else
    echo "All checks passed! Your environment is ready."
    exit 0
fi
