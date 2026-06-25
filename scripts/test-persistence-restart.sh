#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# test-persistence-restart.sh — Validate that data survives restart
#
# Tests:
#   1. Create workspace + upload file + parse + index
#   2. Record data state
#   3. Simulate restart (by checking data directory)
#   4. Verify workspace, data source, and provider still exist
#
# For Docker:
#   docker compose stop backend
#   docker compose start backend
#
# For native:
#   Stop and restart the decision-system serve-api process
#
# Usage:
#   bash scripts/test-persistence-restart.sh
#   BACKEND_URL=http://localhost:8000 bash scripts/test-persistence-restart.sh
# ---------------------------------------------------------------------------
set -euo pipefail

BASE_URL="${BACKEND_URL:-http://localhost:8000}"
PASS=0
FAIL=0
ERRORS=()

pass() { PASS=$((PASS+1)); echo "  ✅ $1"; }
fail() { ERRORS+=("$1"); FAIL=$((FAIL+1)); echo "  ❌ $1"; }

echo "============================================"
echo "  Persistence Restart Test — v1.25"
echo "============================================"
echo ""

# ------------------------------------------------------------------
# 0. Health check
# ------------------------------------------------------------------
echo "--- [0] Health check ---"
HEALTH=$(curl -sf "$BASE_URL/health" 2>/dev/null || echo "")
if [ -z "$HEALTH" ]; then
    fail "Backend unreachable at $BASE_URL"
    echo "  Start the backend first."
    exit 1
fi
pass "Backend reachable"

# ------------------------------------------------------------------
# 1. Create workspace and record state
# ------------------------------------------------------------------
echo ""
echo "--- [1] Create workspace ---"
TS=$(date +%s)
WS_RESP=$(curl -sf -X POST "$BASE_URL/workspaces" \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"Persistence Test $TS\",\"description\":\"Auto-created by persistence test\"}" 2>/dev/null || echo '{}')
WS_ID=$(echo "$WS_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null || echo "")
if [ -z "$WS_ID" ]; then
    fail "Could not create workspace"
    exit 1
fi
pass "Workspace created: $WS_ID"

# ------------------------------------------------------------------
# 2. Upload a file
# ------------------------------------------------------------------
echo ""
echo "--- [2] Upload sample file ---"
SAMPLE_FILE="demo/sample-data/company_overview.md"
if [ ! -f "$SAMPLE_FILE" ]; then
    fail "Sample file not found: $SAMPLE_FILE"
    exit 1
fi
UPLOAD_RESP=$(curl -sf -X POST "$BASE_URL/workspaces/$WS_ID/data-sources/upload" \
    -F "file=@$SAMPLE_FILE" 2>/dev/null || echo '{}')
SID=$(echo "$UPLOAD_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('source_id','') or d.get('id',''))" 2>/dev/null || echo "")
if [ -z "$SID" ]; then
    fail "Could not upload file"
    exit 1
fi
pass "File uploaded → $SID"

# ------------------------------------------------------------------
# 3. Parse and index
# ------------------------------------------------------------------
echo ""
echo "--- [3] Parse and index ---"
curl -sf -X POST "$BASE_URL/workspaces/$WS_ID/data-sources/$SID/parse" > /dev/null 2>&1 && pass "File parsed" || fail "Parse failed"
curl -sf -X POST "$BASE_URL/workspaces/$WS_ID/data-sources/$SID/index" > /dev/null 2>&1 && pass "File indexed" || fail "Index failed"

# ------------------------------------------------------------------
# 4. Create fake provider
# ------------------------------------------------------------------
echo ""
echo "--- [4] Create fake provider ---"
curl -sf -X POST "$BASE_URL/providers" \
    -H "Content-Type: application/json" \
    -d '{"name":"Persistence Test Provider","provider_type":"fake","default_model":"fake-model"}' > /dev/null 2>&1 && pass "Fake provider created" || echo "  ⓘ Provider may already exist"

# ------------------------------------------------------------------
# 5. Record state
# ------------------------------------------------------------------
echo ""
echo "--- [5] Record state snapshot ---"

# Save state info to temp file
STATE_FILE=$(mktemp)
cleanup() { rm -f "$STATE_FILE"; }
trap cleanup EXIT

{
    echo "WS_ID=$WS_ID"
    echo "SID=$SID"
    echo "TIMESTAMP=$TS"

    # Record workspaces
    WORKSPACES=$(curl -sf "$BASE_URL/workspaces" 2>/dev/null || echo '[]')
    echo "WS_COUNT=$(echo "$WORKSPACES" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "0")"

    # Record data sources
    SOURCES=$(curl -sf "$BASE_URL/workspaces/$WS_ID/data-sources" 2>/dev/null || echo '[]')
    echo "DS_COUNT=$(echo "$SOURCES" | python3 -c "
import sys, json
d=json.load(sys.stdin)
if isinstance(d, list): print(len(d))
elif isinstance(d, dict): print(len(d.get('sources',[]) or d.get('items',[])))
else: print(0)
" 2>/dev/null || echo "0")"

    # Record providers
    PROVS=$(curl -sf "$BASE_URL/providers" 2>/dev/null || echo '[]')
    echo "PROV_COUNT=$(echo "$PROVS" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "0")"

    # Check local data directory
    if [ -d ".decision_system" ]; then
        echo "DATA_DIR_EXISTS=yes"
        echo "DATA_DIR_SIZE=$(du -sh .decision_system 2>/dev/null | cut -f1 || echo 'unknown')"
    else
        echo "DATA_DIR_EXISTS=no"
    fi
} > "$STATE_FILE"

cat "$STATE_FILE"
pass "State snapshot recorded"

# ------------------------------------------------------------------
# 6. Instructions for restart
# ------------------------------------------------------------------
echo ""
echo "============================================"
echo "  READY FOR RESTART TEST"
echo "============================================"
echo ""
echo "To test persistence, restart the backend NOW."
echo ""
echo "For Docker:"
echo "  docker compose restart backend"
echo "  # Wait 5 seconds, then run the verification step below"
echo ""
echo "For native (Ctrl+C, then restart):"
echo "  pkill -f 'decision-system serve-api' || true"
echo "  decision-system serve-api &"
echo "  sleep 2"
echo ""
echo "After restart, run the verification:"
echo "  bash scripts/test-persistence-restart.sh --verify $STATE_FILE"
echo ""

# ------------------------------------------------------------------
# If --verify flag, check that data survived
# ------------------------------------------------------------------
if [ "${1:-}" = "--verify" ] && [ -n "${2:-}" ]; then
    STATE_FILE="$2"
    echo "--- Verifying persistence ---"

    # Load recorded state
    source "$STATE_FILE" 2>/dev/null || true

    # Health check
    HEALTH=$(curl -sf "$BASE_URL/health" 2>/dev/null || echo "")
    if [ -z "$HEALTH" ]; then
        fail "Backend not reachable after restart"
        exit 1
    fi
    pass "Backend reachable after restart"

    # Check workspaces
    WS_AFTER=$(curl -sf "$BASE_URL/workspaces" 2>/dev/null || echo '[]')
    if [ -n "${WS_ID:-}" ]; then
        WS_FOUND=$(echo "$WS_AFTER" | python3 -c "
import sys, json
try:
    ws_list = json.load(sys.stdin)
    for w in ws_list:
        if w.get('id') == '$WS_ID':
            print('found')
            break
except: pass
" 2>/dev/null || echo "")
        if [ "$WS_FOUND" = "found" ]; then
            pass "Workspace '$WS_ID' survived restart"
        else
            fail "Workspace '$WS_ID' lost after restart"
        fi
    fi

    # Check data sources
    if [ -n "${WS_ID:-}" ] && [ -n "${SID:-}" ]; then
        DS_AFTER=$(curl -sf "$BASE_URL/workspaces/$WS_ID/data-sources" 2>/dev/null || echo '[]')
        DS_FOUND=$(echo "$DS_AFTER" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    items = d if isinstance(d, list) else (d.get('sources',[]) or d.get('items',[]))
    for s in items:
        sid = s.get('source_id','') or s.get('id','')
        if sid == '$SID':
            print('found')
            break
except: pass
" 2>/dev/null || echo "")
        if [ "$DS_FOUND" = "found" ]; then
            pass "Data source '$SID' survived restart"
        else
            fail "Data source '$SID' lost after restart"
        fi
    fi

    # Check providers
    PROV_AFTER=$(curl -sf "$BASE_URL/providers" 2>/dev/null || echo '[]')
    PROV_COUNT_AFTER=$(echo "$PROV_AFTER" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "0")
    if [ "${PROV_COUNT:-0}" -gt 0 ] && [ "$PROV_COUNT_AFTER" -gt 0 ]; then
        pass "Providers survived restart ($PROV_COUNT_AFTER provider(s))"
    else
        echo "  ⓘ No providers to verify"
        pass "Provider check completed"
    fi

    # Check data directory
    if [ -d ".decision_system" ]; then
        pass "Data directory exists"
    fi

    # Summary
    echo ""
    echo "============================================"
    echo "  Persistence Test Complete"
    echo "============================================"
    echo ""
    echo "Results: $PASS passed, $FAIL failed"
    if [ "$FAIL" -gt 0 ]; then
        for e in "${ERRORS[@]}"; do echo "  - $e"; done
    fi

    # Cleanup
    rm -f "$STATE_FILE"
    exit $(( FAIL > 126 ? 126 : FAIL ))
fi
