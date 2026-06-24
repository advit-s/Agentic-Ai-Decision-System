#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# local-demo-seed.sh — Seed a local demo environment for the workflow builder
#
# Usage:
#   bash scripts/local-demo-seed.sh
#   bash scripts/local-demo-seed.sh --force   # Re-seed even if exists
#
# This script:
#   1. Checks backend health
#   2. Creates a demo workspace (or uses existing)
#   3. Uploads sample data files (text + OCR-required)
#   4. Parses/indexes sample files (OCR triggered automatically)
#   5. Creates or ensures fake provider
#   6. Loads demo workflow template
#   7. Prints next steps
#
# No cloud API keys required. Repeatable: safe to run multiple times
# (existing data is not destroyed unless --force is used).
# ---------------------------------------------------------------------------
set -euo pipefail

FORCE="${1:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

PASS=0
FAIL=0
pass() { PASS=$((PASS+1)); echo "  ✅ $1"; }
fail() { FAIL=$((FAIL+1)); echo "  ❌ $1"; }

BASE_URL="${BACKEND_URL:-http://localhost:8000}"
SAMPLE_DIR="demo/sample-data"

echo "============================================"
echo "  Local Demo Seed Script — v1.25"
echo "============================================"
echo ""

# ------------------------------------------------------------------
# 1. Backend health check
# ------------------------------------------------------------------
echo "--- [1/7] Checking backend health ---"
if HEALTH=$(curl -sf -o /dev/null -w "%{http_code}" "$BASE_URL/health" 2>/dev/null); then
  pass "Backend reachable at $BASE_URL (HTTP $HEALTH)"
else
  fail "Backend unreachable at $BASE_URL. Start the API or Docker first."
  echo ""
  echo "  Start with:  decision-system serve-api"
  echo "  Or Docker:   docker compose up"
  exit 1
fi

VERSION=$(curl -sf "$BASE_URL/health" 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('version','unknown'))" 2>/dev/null || echo "unknown")
echo "  Backend version: $VERSION"

# ------------------------------------------------------------------
# 2. Create demo workspace
# ------------------------------------------------------------------
echo ""
echo "--- [2/7] Setting up demo workspace ---"

WS_ID=""
# List existing workspaces
WS_LIST=$(curl -sf "$BASE_URL/workspaces" 2>/dev/null || echo '[]')
DEMO_WS=$(echo "$WS_LIST" | python3 -c "
import sys, json
try:
    workspaces = json.load(sys.stdin)
    for w in workspaces:
        if w.get('name','').lower().startswith('demo'):
            print(f\"{w.get('id','')}|{w.get('name','')}\")
except: pass
" 2>/dev/null || true)

if [ -n "$DEMO_WS" ] && [ "$FORCE" != "--force" ]; then
    WS_ID=$(echo "$DEMO_WS" | cut -d'|' -f1)
    WS_NAME=$(echo "$DEMO_WS" | cut -d'|' -f2)
    pass "Demo workspace exists: $WS_NAME ($WS_ID)"
else
    if [ -n "$DEMO_WS" ] && [ "$FORCE" = "--force" ]; then
        WS_ID=$(echo "$DEMO_WS" | cut -d'|' -f1)
        echo "  Force mode: removing existing demo workspace..."
        curl -sf -X DELETE "$BASE_URL/workspaces/$WS_ID" > /dev/null 2>&1 || true
    fi
    WS_RESP=$(curl -sf -X POST "$BASE_URL/workspaces" \
        -H "Content-Type: application/json" \
        -d '{"name":"Demo Workspace","description":"Local demo workspace for workflow builder"}' 2>/dev/null || echo "")
    WS_ID=$(echo "$WS_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null || echo "")
    if [ -n "$WS_ID" ]; then
        pass "Created demo workspace: $WS_ID"
    else
        fail "Failed to create demo workspace"
        WS_ID="demo-workspace"
    fi
fi

# ------------------------------------------------------------------
# 3. Upload sample data files
# ------------------------------------------------------------------
echo ""
echo "--- [3/7] Uploading sample data ---"

if [ ! -d "$SAMPLE_DIR" ]; then
    fail "Sample data directory not found: $SAMPLE_DIR"
    echo "  Run scripts/generate-sample-data.sh first"
    exit 1
fi

UPLOADED=0
for fpath in "$SAMPLE_DIR"/*; do
    fname=$(basename "$fpath")
    echo "  Uploading $fname..."
    RESP=$(curl -sf -X POST "$BASE_URL/workspaces/$WS_ID/data-sources/upload" \
        -F "file=@$fpath" 2>/dev/null || echo '{"error":"upload failed"}')
    SID=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('source_id','') or json.load(sys.stdin).get('id',''))" 2>/dev/null || echo "")
    if [ -n "$SID" ]; then
        pass "Uploaded $fname → $SID"
        UPLOADED=$((UPLOADED+1))
    else
        fail "Upload failed for $fname: $(echo "$RESP" | head -c 200)"
    fi
done

if [ "$UPLOADED" -eq 0 ]; then
    fail "No files uploaded"
    exit 1
fi

# ------------------------------------------------------------------
# 4. Parse and index files
# ------------------------------------------------------------------
echo ""
echo "--- [4/7] Parsing and indexing data ---"

# Get list of data sources
SOURCES=$(curl -sf "$BASE_URL/workspaces/$WS_ID/data-sources" 2>/dev/null || echo '[]')
SOURCE_IDS=$(echo "$SOURCES" | python3 -c "
import sys, json
try:
    sources = json.load(sys.stdin)
    if isinstance(sources, list):
        for s in sources:
            sid = s.get('source_id','') or s.get('id','')
            if sid:
                print(sid)
    elif isinstance(sources, dict):
        items = sources.get('sources',[]) or sources.get('items',[])
        for s in items:
            sid = s.get('source_id','') or s.get('id','')
            if sid:
                print(sid)
except: pass
" 2>/dev/null || true)

PARSED=0
INDEXED=0
for SID in $SOURCE_IDS; do
    echo "  Parsing $SID..."
    PARSE_RESP=$(curl -sf -X POST "$BASE_URL/workspaces/$WS_ID/data-sources/$SID/parse" 2>/dev/null || echo '{"error":"parse failed"}')
    if echo "$PARSE_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print('error' if 'error' in d else 'ok')" 2>/dev/null | grep -q 'ok'; then
        pass "Parsed $SID"
        PARSED=$((PARSED+1))

        echo "  Indexing $SID..."
        INDEX_RESP=$(curl -sf -X POST "$BASE_URL/workspaces/$WS_ID/data-sources/$SID/index" 2>/dev/null || echo '{"error":"index failed"}')
        if echo "$INDEX_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print('error' if 'error' in d else 'ok')" 2>/dev/null | grep -q 'ok'; then
            pass "Indexed $SID"
            INDEXED=$((INDEXED+1))
        else
            fail "Index failed for $SID: $(echo "$INDEX_RESP" | head -c 200)"
        fi
    else
        fail "Parse failed for $SID: $(echo "$PARSE_RESP" | head -c 200)"
    fi
done

# ------------------------------------------------------------------
# 5. Create or ensure fake provider
# ------------------------------------------------------------------
echo ""
echo "--- [5/7] Configuring fake provider ---"

# Check existing providers
PROV_LIST=$(curl -sf "$BASE_URL/providers" 2>/dev/null || echo '[]')
HAS_FAKE=$(echo "$PROV_LIST" | python3 -c "
import sys, json
try:
    providers = json.load(sys.stdin)
    for p in providers:
        pt = p.get('provider_type','') or p.get('type','')
        if 'fake' in str(pt).lower() or 'fake' in p.get('name','').lower():
            print(p.get('id','') or p.get('provider_id',''))
            break
except: pass
" 2>/dev/null || true)

if [ -n "$HAS_FAKE" ]; then
    pass "Fake provider already configured ($HAS_FAKE)"
else
    PROV_RESP=$(curl -sf -X POST "$BASE_URL/providers" \
        -H "Content-Type: application/json" \
        -d '{"name":"Fake Demo Provider","provider_type":"fake","default_model":"fake-model"}' 2>/dev/null || echo '{"error":"create failed"}')
    PID=$(echo "$PROV_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id','') or json.load(sys.stdin).get('provider_id',''))" 2>/dev/null || echo "")
    if [ -n "$PID" ]; then
        pass "Created fake provider: $PID"
    else
        fail "Failed to create fake provider: $(echo "$PROV_RESP" | head -c 200)"
    fi
fi

# ------------------------------------------------------------------
# 6. Create demo workflow template
# ------------------------------------------------------------------
echo ""
echo "--- [6/7] Creating demo workflow template ---"

WF_RESP=$(curl -sf -X POST "$BASE_URL/workspaces/$WS_ID/workflows" \
    -H "Content-Type: application/json" \
    -d '{
        "name":"Local Trust Report Demo",
        "description":"End-to-end demo: evidence search → synthesis → verification → contradiction scan → trust report",
        "nodes": [
            {"id":"ev-search","type":"evidence_search","config":{"query":"billing system migration risks","limit":10}},
            {"id":"ev-synth","type":"evidence_synthesis","config":{"provider":"fake","auto_verify":true}},
            {"id":"claim-verify","type":"claim_verification","config":{"auto_verify":true}},
            {"id":"contradiction-scan","type":"contradiction_scan","config":{}},
            {"id":"review-gate","type":"review_gate","config":{"optional":true}},
            {"id":"trust-report","type":"trust_report","config":{"format":"markdown"}}
        ],
        "edges": [
            {"source":"ev-search","target":"ev-synth"},
            {"source":"ev-synth","target":"claim-verify"},
            {"source":"claim-verify","target":"contradiction-scan"},
            {"source":"contradiction-scan","target":"review-gate"},
            {"source":"review-gate","target":"trust-report"}
        ]
    }' 2>/dev/null || echo '{"error":"workflow create failed"}')

WF_ID=$(echo "$WF_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('id','') or d.get('workflow_id',''))" 2>/dev/null || echo "")
if [ -n "$WF_ID" ]; then
    pass "Created demo workflow: $WF_ID"
else
    fail "Failed to create workflow: $(echo "$WF_RESP" | head -c 200)"
fi

# ------------------------------------------------------------------
# 7. Summary and next steps
# ------------------------------------------------------------------
echo ""
echo "============================================"
echo "  Demo Seed Complete!"
echo "============================================"
echo ""
echo "Summary:"
echo "  Workspace:     $WS_ID"
echo "  Files uploaded: $UPLOADED"
echo "  Files parsed:   $PARSED"
echo "  Files indexed:  $INDEXED"
echo "  Workflow:      ${WF_ID:-not created}"
echo ""
echo "Next steps:"
echo "  1. Open the app:  http://localhost:3000"
echo "  2. Select workspace: 'Demo Workspace'"
echo "  3. Go to Workflow Builder → Load 'Local Trust Report Demo'"
echo "  4. Click Execute"
echo "  5. Open Claim Ledger → Verify Claims"
echo "  6. Open Trust Dashboard → Generate Report"
echo "  7. Open Reports → Export Markdown"
echo ""
echo "Reset:"
echo "  docker compose down -v    # Remove all data"
echo "  bash scripts/local-demo-seed.sh --force  # Re-seed"
echo ""

if [ "$FAIL" -gt 0 ]; then
    echo "⚠️  $FAIL steps had warnings/failures (demo may still work)"
    exit 0  # Non-fatal exit
fi
