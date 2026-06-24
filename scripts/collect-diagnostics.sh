#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# collect-diagnostics.sh — Safe diagnostic collector for beta reviewers
#
# This script collects environment and app diagnostics WITHOUT capturing:
#   - API keys, tokens, or passwords
#   - .env contents
#   - Uploaded documents or evidence chunks
#   - Report contents
#   - Absolute local file contents
#
# Usage:
#   ./scripts/collect-diagnostics.sh
#
# Output:
#   diagnostics/<timestamp>/diagnostics.txt
# ---------------------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_DIR="$PROJECT_DIR/diagnostics/$TIMESTAMP"
OUTPUT_FILE="$OUTPUT_DIR/diagnostics.txt"

mkdir -p "$OUTPUT_DIR"

exec > "$OUTPUT_FILE" 2>&1

echo "============================================"
echo "  Agentic Decision System — Diagnostics"
echo "  Collected: $(date)"
echo "============================================"
echo ""

# --- App version ---
echo "--- App Version ---"
if [ -f "$PROJECT_DIR/src/decision_system/__init__.py" ]; then
  grep "__version__" "$PROJECT_DIR/src/decision_system/__init__.py" | head -1
fi
if [ -f "$PROJECT_DIR/pyproject.toml" ]; then
  grep "^version" "$PROJECT_DIR/pyproject.toml" | head -1
fi
echo ""

# --- Git commit ---
echo "--- Git Commit ---"
if git -C "$PROJECT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Commit: $(git -C "$PROJECT_DIR" rev-parse HEAD 2>/dev/null || echo 'unknown')"
  echo "Branch: $(git -C "$PROJECT_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'unknown')"
else
  echo "Not a git repository"
fi
echo ""

# --- OS info ---
echo "--- OS Info ---"
uname -a 2>/dev/null || echo "uname not available"
cat /etc/os-release 2>/dev/null || cat /etc/*release 2>/dev/null || echo "OS release info not available"
echo ""

# --- Python ---
echo "--- Python ---"
python3 --version 2>/dev/null || python --version 2>/dev/null || echo "Python not found"
which python3 2>/dev/null || which python 2>/dev/null || echo "Python not in PATH"
echo ""

# --- Node.js ---
echo "--- Node.js ---"
node --version 2>/dev/null || echo "Node.js not found"
npm --version 2>/dev/null || echo "npm not found"
echo ""

# --- Docker ---
echo "--- Docker ---"
docker --version 2>/dev/null || echo "Docker not found"
docker compose version 2>/dev/null || echo "Docker Compose not found"
echo ""

# --- Doctor output ---
echo "--- Doctor Output ---"
if [ -f "$PROJECT_DIR/scripts/doctor-local.sh" ]; then
  bash "$PROJECT_DIR/scripts/doctor-local.sh" --quiet 2>/dev/null || echo "Doctor script failed"
else
  echo "doctor-local.sh not found"
fi
echo ""

# --- System status (if backend running) ---
echo "--- System Status ---"
if command -v curl &>/dev/null; then
  curl -s http://localhost:8000/system/status 2>/dev/null || echo "Backend not running at :8000"
  echo ""
  curl -s http://localhost:8000/health 2>/dev/null || echo "Health endpoint not available"
else
  echo "curl not available"
fi
echo ""

# --- Validation summary (if available) ---
echo "--- Recent Validation ---"
VALIDATION_LOG="$PROJECT_DIR/.decision_system/logs/validation-last.txt"
if [ -f "$VALIDATION_LOG" ]; then
  cat "$VALIDATION_LOG" 2>/dev/null | tail -20
else
  echo "No validation log found (run ./scripts/validate-local.sh to generate)"
fi
echo ""

# --- Script existence ---
echo "--- Scripts Check ---"
for script in setup-local.sh start-local.sh stop-local.sh doctor-local.sh validate-local.sh backup-local-data.sh reset-local-data.sh; do
  if [ -f "$PROJECT_DIR/scripts/$script" ]; then
    echo "✅ $script exists and is executable: $(test -x "$PROJECT_DIR/scripts/$script" && echo 'yes' || echo 'no')"
  else
    echo "❌ $script missing"
  fi
done
echo ""

# --- Frontend package info ---
echo "--- Frontend Info ---"
if [ -f "$PROJECT_DIR/web/workflow-builder/package.json" ]; then
  grep '"version"' "$PROJECT_DIR/web/workflow-builder/package.json" | head -1
else
  echo "Frontend package.json not found"
fi
echo ""

# --- Backend package info ---
echo "--- Backend Info ---"
if [ -f "$PROJECT_DIR/pyproject.toml" ]; then
  grep "^version\|^name\|^requires-python" "$PROJECT_DIR/pyproject.toml" | head -5
fi
echo ""

# --- Safety note ---
echo "============================================"
echo "  Diagnostics collected safely."
echo "  No secrets, documents, or report contents"
echo "  have been included."
echo ""
echo "  OUTPUT: $OUTPUT_FILE"
echo "============================================"

# Print output path to stdout (goes to terminal too)
echo ""
echo "Diagnostics saved to: $OUTPUT_FILE"
