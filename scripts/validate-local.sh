#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# validate-local.sh — CI-ready local validation for Agentic Decision System
#
# Run this before committing or pushing to confirm the repo is in a clean,
# release-baseline state.
#
# Usage:
#   ./scripts/validate-local.sh          # stop on first failure
#   ./scripts/validate-local.sh --summarize  # run all, then summarize
#
# Optional Docker smoke can be run separately:
#   docker compose up --build && ./scripts/local-smoke-test.sh
#   ./scripts/e2e-local-demo-smoke.sh
#
# Requirements:
#   - Python virtual environment auto-detected (.venv/bin/python) or system python
#   - Node.js and npm installed
# ---------------------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

# Auto-detect venv python
if [ -f "$PROJECT_DIR/.venv/bin/python" ]; then
  PYTHON="$PROJECT_DIR/.venv/bin/python"
else
  PYTHON="python"
fi

SUMMARY_MODE=false
if [[ "${1:-}" == "--summarize" ]]; then
  SUMMARY_MODE=true
fi

PASS=0
FAIL=0
FAIL_CMDS=""

run_check() {
  local name="$1"
  shift
  echo ""
  echo "=== $name ==="
  if "$@"; then
    echo "  ✅ PASS: $name"
    PASS=$((PASS + 1))
  else
    echo "  ❌ FAIL: $name"
    FAIL=$((FAIL + 1))
    FAIL_CMDS="$FAIL_CMDS  - $name"$'\n'
    if ! $SUMMARY_MODE; then
      exit 1
    fi
  fi
}

# ---------------------------------------------------------------------------
# 1. Git hygiene
# ---------------------------------------------------------------------------
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  run_check "git diff --check" git diff --check
else
  echo "  ⏭️  SKIP: git diff --check (not in a git repository)"
fi

# ---------------------------------------------------------------------------
# 2. Backend targeted tests
# ---------------------------------------------------------------------------
run_check "tests/test_security.py" $PYTHON -m pytest tests/test_security.py -q
run_check "tests/test_graph_api.py" $PYTHON -m pytest tests/test_graph_api.py -q
run_check "tests/test_data_sources/" $PYTHON -m pytest tests/test_data_sources/ -q
run_check "tests/test_verification" $PYTHON -m pytest tests/test_verification -q
run_check "tests/test_providers" $PYTHON -m pytest tests/test_providers -q
run_check "tests/test_workflow_engine/test_api.py" $PYTHON -m pytest tests/test_workflow_engine/test_api.py -q
run_check "tests/test_connectors.py" $PYTHON -m pytest tests/test_connectors.py -q
run_check "tests/test_connector_sync.py" $PYTHON -m pytest tests/test_connector_sync.py -q
run_check "tests/test_api_connector.py" $PYTHON -m pytest tests/test_api_connector.py -q
run_check "tests/test_connector_setup.py" $PYTHON -m pytest tests/test_connector_setup.py -q

# ---------------------------------------------------------------------------
# 3. Frontend tests
# ---------------------------------------------------------------------------
if [ -d "$PROJECT_DIR/web/workflow-builder/node_modules" ]; then
  run_check "npm test (frontend)" bash -c "cd web/workflow-builder && npm test 2>&1 | tail -5"
else
  echo "  ⏭️  SKIP: npm test (node_modules not found — run 'npm install' first)"
fi

# ---------------------------------------------------------------------------
# 4. Frontend build
# ---------------------------------------------------------------------------
run_check "npm run build" bash -c "cd web/workflow-builder && npm run build 2>&1 | tail -5"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "========================================="
echo "  Validation complete"
echo "  Passed: $PASS"
echo "  Failed: $FAIL"
if [ "$FAIL" -gt 0 ]; then
  echo ""
  echo "  Failed checks:"
  echo -n "$FAIL_CMDS"
fi
echo "========================================="
exit $FAIL
