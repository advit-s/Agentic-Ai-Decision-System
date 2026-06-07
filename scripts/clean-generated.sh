#!/usr/bin/env bash
set -euo pipefail

# Dry-run by default; pass --force to actually delete.
FORCE="${1:-}"
if [[ "${FORCE}" == "--force" ]]; then
    echo "=== Removing generated/cache files (force) ==="
    python -m decision_system.devtools.clean_generated --force
else
    echo "=== Dry run: would remove generated/cache files ==="
    echo "    Re-run with --force to actually delete: ./scripts/clean-generated.sh --force"
    python -m decision_system.devtools.clean_generated
fi
