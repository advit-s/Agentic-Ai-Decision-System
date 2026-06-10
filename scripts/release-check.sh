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

SUCCESSES=0
FAILURES=0

check() {
    local name="$1"
    local result="$2"
    if [ "$result" = "0" ]; then
        echo "[PASS] $name"
        SUCCESSES=$((SUCCESSES + 1))
    else
        echo "[FAIL] $name"
        FAILURES=$((FAILURES + 1))
    fi
}

# Git detection: check if we're inside a Git repository
# Returns 0 if yes, 1 if no
is_git_repo() {
    git rev-parse --is-inside-work-tree >/dev/null 2>&1
}

# ---------------------------------------------------------------------------
# Checks 1-6 use git ls-files when inside a Git repo, otherwise fall back to
# safe filesystem checks (e.g. find/grep on . to see if artifacts exist).
# ---------------------------------------------------------------------------
IN_GIT=0
if is_git_repo; then
    IN_GIT=1
    echo "[INFO] Git repository detected — using git ls-files for tracking checks"
else
    echo "[INFO] Not inside a Git repository — using filesystem fallback checks"
fi

# Helper: return 0 when a matching file or directory exists, 1 otherwise.
# Accepts any find arguments and passes them directly.
has_match() {
    find . "$@" -not -path './.venv/*' -not -path './.git/*' 2>/dev/null -print -quit | grep -q .
}

# 1. No __pycache__ in tracked files
PYCACHE=0
if [ "$IN_GIT" -eq 1 ]; then
    PYCACHE=$(git ls-files | grep -c "__pycache__" || true)
elif has_match -name __pycache__ -type d; then
    PYCACHE=1
fi
check "No __pycache__ in tracked files" "$([ "$PYCACHE" -eq 0 ] && echo 0 || echo 1)"

# 2. No .pyc in tracked files
PYC=0
if [ "$IN_GIT" -eq 1 ]; then
    PYC=$(git ls-files | grep -c "\.pyc$" || true)
elif has_match -name '*.pyc'; then
    PYC=1
fi
check "No .pyc files in tracked files" "$([ "$PYC" -eq 0 ] && echo 0 || echo 1)"

# 3. No .decision_system/ tracked
DS=0
if [ "$IN_GIT" -eq 1 ]; then
    DS=$(git ls-files | grep -c "^\.decision_system/" || true)
else
    DS=$([ -d ".decision_system" ] && echo 1 || echo 0)
fi
check "No .decision_system/ tracked" "$([ "$DS" -eq 0 ] && echo 0 || echo 1)"

# 4. No datasets/ tracked
DATASETS=0
if [ "$IN_GIT" -eq 1 ]; then
    DATASETS=$(git ls-files | grep -c "^datasets/" || true)
else
    DATASETS=$([ -d "datasets" ] && echo 1 || echo 0)
fi
check "No datasets/ tracked" "$([ "$DATASETS" -eq 0 ] && echo 0 || echo 1)"

# 5. No .env tracked
ENV_CHECK=0
if [ "$IN_GIT" -eq 1 ]; then
    ENV_CHECK=$(git ls-files | grep -c "^\.env$" || true)
else
    ENV_CHECK=$([ -f ".env" ] && echo 1 || echo 0)
fi
check "No .env tracked" "$([ "$ENV_CHECK" -eq 0 ] && echo 0 || echo 1)"

# 6. No secrets in tracked source (basic grep check)
SECRETS=0
if [ "$IN_GIT" -eq 1 ]; then
    SECRETS=$(git ls-files | grep -E '\.(py|md|txt|json|yaml|yml|toml|cfg|ini|sh)$' | grep -v '__pycache__' | grep -v '.decision_system' | while read f; do
        grep -lE '(?i)(sk-[a-zA-Z0-9]{20,}|AKIA[A-Z0-9]{16}|nvapi-[a-zA-Z0-9\-_]{20,})' "$f" 2>/dev/null || true
    done | grep -c . || true)
else
    SECRETS=0
    if find . \( -name '*.py' -o -name '*.md' -o -name '*.txt' -o -name '*.json' -o -name '*.yaml' -o -name '*.yml' -o -name '*.toml' -o -name '*.cfg' -o -name '*.ini' -o -name '*.sh' \) \
        -not -path './.venv/*' -not -path './.git/*' -not -path './.decision_system/*' \
        -exec grep -lE '(?i)(sk-[a-zA-Z0-9]{20,}|AKIA[A-Z0-9]{16}|nvapi-[a-zA-Z0-9\-_]{20,})' {} + 2>/dev/null -print -quit | grep -q .; then
        SECRETS=1
    fi
fi
check "No obvious secrets in tracked source" "$([ "$SECRETS" -eq 0 ] && echo 0 || echo 1)"

# 7. Package install works
INSTALL_OK=0
(pip install -e ".[dev]" --break-system-packages >/dev/null 2>&1) || \
  (pip install -e ".[dev]" >/dev/null 2>&1) || \
  INSTALL_OK=1
check "Package install works" "$INSTALL_OK"

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

# 11. validate-demo-data
DEMO_VALID_RESULT=0
decision-system validate-demo-data >/dev/null 2>&1 || DEMO_VALID_RESULT=1
check "validate-demo-data passes" "$([ "$DEMO_VALID_RESULT" -eq 0 ] && echo 0 || echo 1)"

# 10. check-hygiene
HYGIENE_RESULT=0
decision-system check-hygiene >/dev/null 2>&1 || HYGIENE_RESULT=1
check "check-hygiene passes" "$([ "$HYGIENE_RESULT" -eq 0 ] && echo 0 || echo 1)"

echo ""
echo "Release Check: $SUCCESSES passed, $FAILURES failed"
if [ "$FAILURES" -gt 0 ]; then
    echo "RESULT: NOT READY FOR RELEASE"
    exit 1
else
    echo "RESULT: READY FOR RELEASE"
fi
