#!/usr/bin/env bash
# release-check.sh - Verify the repo is clean and ready for release
# Checks:
#   1. No __pycache__ directories in tracked files
#   2. No .pyc files in tracked files
#   3. No generated .decision_system/ tracked
#   4. No raw datasets/ tracked
#   5. No .env tracked
#   6. No secrets in tracked source
#   7. Package install works
#   8. Tests pass
#   9. CLI import is fast
#  10. check-hygiene passes

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

PASS=0
FAIL=0

check() {
    local name="$1"
    local result="$2"
    if [ "$result" = "0" ]; then
        echo "[PASS] $name"
        PASS=$((PASS + 1))
    else
        echo "[FAIL] $name"
        FAIL=$((FAIL + 1))
    fi
}

# 1. No __pycache__ in tracked files
PYCACHE=$(git ls-files | grep -c "__pycache__" || true)
check "No __pycache__ in tracked files" "$([ "$PYCACHE" -eq 0 ] && echo 0 || echo 1)"

# 2. No .pyc in tracked files
PYC=$(git ls-files | grep -c "\.pyc$" || true)
check "No .pyc files in tracked files" "$([ "$PYC" -eq 0 ] && echo 0 || echo 1)"

# 3. No .decision_system/ tracked
DS=$(git ls-files | grep -c "^\.decision_system/" || true)
check "No .decision_system/ tracked" "$([ "$DS" -eq 0 ] && echo 0 || echo 1)"

# 4. No datasets/ tracked
DATASETS=$(git ls-files | grep -c "^datasets/" || true)
check "No datasets/ tracked" "$([ "$DATASETS" -eq 0 ] && echo 0 || echo 1)"

# 5. No .env tracked
ENV=$(git ls-files | grep -c "^\.env$" || true)
check "No .env tracked" "$([ "$ENV" -eq 0 ] && echo 0 || echo 1)"

# 6. No secrets in tracked source (basic grep check)
SECRETS=$(git ls-files | grep -E '\.(py|md|txt|json|yaml|yml|toml|cfg|ini|sh)$' | grep -v '__pycache__' | grep -v '.decision_system' | while read f; do
    grep -lE '(?i)(sk-[a-zA-Z0-9]{20,}|AKIA[A-Z0-9]{16}|nvapi-[a-zA-Z0-9\-_]{20,})' "$f" 2>/dev/null || true
done | grep -c . || true)
check "No obvious secrets in tracked source" "$([ "$SECRETS" -eq 0 ] && echo 0 || echo 1)"

# 7. Package install works
pip install -e ".[dev]" --break-system-packages >/dev/null 2>&1 || pip install -e ".[dev]" >/dev/null 2>&1
check "Package install works" "0"

# 8. Tests pass
TEST_RESULT=0
python -m pytest -q --tb=no 2>/dev/null || TEST_RESULT=1
check "Tests pass" "$([ "$TEST_RESULT" -eq 0 ] && echo 0 || echo 1)"

# 9. CLI import is fast
IMPORT_RESULT=0
python -c "
import time
t = time.time()
import decision_system.cli
elapsed = time.time() - t
print(f'CLI import: {elapsed:.3f}s')
assert elapsed < 3.0, f'Too slow: {elapsed:.3f}s'
" 2>/dev/null || IMPORT_RESULT=1
check "CLI import under 3s" "$([ "$IMPORT_RESULT" -eq 0 ] && echo 0 || echo 1)"

# 10. check-hygiene
HYGIENE_RESULT=0
decision-system check-hygiene >/dev/null 2>&1 || HYGIENE_RESULT=1
check "check-hygiene passes" "$([ "$HYGIENE_RESULT" -eq 0 ] && echo 0 || echo 1)"

echo ""
echo "Release Check: $PASS passed, $FAIL failed"
if [ "$FAIL" -gt 0 ]; then
    echo "RESULT: NOT READY FOR RELEASE"
    exit 1
else
    echo "RESULT: READY FOR RELEASE"
fi
