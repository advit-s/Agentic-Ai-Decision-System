#!/usr/bin/env bash
set -euo pipefail

echo "=== Removing generated/cache files ==="
find . -type d -name __pycache__ -prune -exec rm -rf {} +
rm -rf .pytest_cache
rm -rf .decision_system
echo "Done."
