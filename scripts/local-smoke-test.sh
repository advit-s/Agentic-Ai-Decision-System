#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# local-smoke-test.sh — Quick verification that the local stack is running.
# Checks backend, frontend, and nginx proxy routes.
# No cloud API keys required.
# ---------------------------------------------------------------------------
set -euo pipefail

PASS=0
FAIL=0

pass() { PASS=$((PASS+1)); echo "  ✅ PASS: $1"; }
fail() { FAIL=$((FAIL+1)); echo "  ❌ FAIL: $1"; }

echo "=== Local Smoke Tests ==="
echo ""

# ------------------------------------------------------------------
# 1. Backend health
# ------------------------------------------------------------------
echo "--- Backend ---"
if HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health 2>/dev/null); then
  if [ "$HEALTH" = "200" ]; then
    pass "GET http://localhost:8000/health → $HEALTH"
  else
    fail "GET http://localhost:8000/health → $HEALTH (expected 200)"
  fi
else
  fail "Backend unreachable at http://localhost:8000/health"
fi

# Backend version
VERSION=$(curl -s http://localhost:8000/health 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('version','unknown'))" 2>/dev/null || echo "unknown")
echo "  Backend version: $VERSION"

# ------------------------------------------------------------------
# 2. Frontend (served by nginx)
# ------------------------------------------------------------------
echo "--- Frontend ---"
if FE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/ 2>/dev/null); then
  if [ "$FE" = "200" ]; then
    pass "GET http://localhost:3000/ → $FE"
  else
    fail "GET http://localhost:3000/ → $FE (expected 200)"
  fi
else
  fail "Frontend unreachable at http://localhost:3000/"
fi

# ------------------------------------------------------------------
# 3. Health through nginx proxy
# ------------------------------------------------------------------
echo "--- Nginx Proxy ---"
if PHEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/health 2>/dev/null); then
  if [ "$PHEALTH" = "200" ]; then
    pass "GET http://localhost:3000/health (via nginx) → $PHEALTH"
  else
    fail "GET http://localhost:3000/health (via nginx) → $PHEALTH (expected 200)"
  fi
else
  fail "Nginx proxy health unreachable"
fi

# ------------------------------------------------------------------
# 4. Workflows API through nginx proxy
# ------------------------------------------------------------------
if WF=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/workflows 2>/dev/null); then
  if [ "$WF" = "200" ]; then
    pass "GET http://localhost:3000/workflows (via nginx) → $WF"
  else
    fail "GET http://localhost:3000/workflows (via nginx) → $WF (expected 200)"
  fi
else
  fail "Workflows API unreachable via nginx"
fi

# ------------------------------------------------------------------
# 5. Workspaces API through nginx proxy
# ------------------------------------------------------------------
if WS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/workspaces/_all_/overview 2>/dev/null); then
  if [ "$WS" = "200" ]; then
    pass "GET http://localhost:3000/workspaces/_all_/overview (via nginx) → $WS"
  else
    fail "GET http://localhost:3000/workspaces/_all_/overview (via nginx) → $WS (expected 200)"
  fi
else
  fail "Workspaces API unreachable via nginx"
fi

# ------------------------------------------------------------------
# 6. Claims API through nginx proxy
# ------------------------------------------------------------------
if CL=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/workspaces/_all_/claims 2>/dev/null); then
  if [ "$CL" = "200" ]; then
    pass "GET http://localhost:3000/workspaces/_all_/claims (via nginx) → $CL"
  else
    fail "GET http://localhost:3000/workspaces/_all_/claims (via nginx) → $CL (expected 200)"
  fi
else
  fail "Claims API unreachable via nginx"
fi

# ------------------------------------------------------------------
# Summary
# ------------------------------------------------------------------
echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
exit 0
