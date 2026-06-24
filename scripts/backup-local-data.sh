#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# backup-local-data.sh — Backup local .decision_system data
#
# Creates a timestamped backup archive in:
#   .decision_system/backups/<timestamp>.tar.gz
#
# Usage:
#   ./scripts/backup-local-data.sh                  # Normal backup
#   ./scripts/backup-local-data.sh /path/to/backup  # Custom output dir
# ---------------------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

DATA_DIR=".decision_system"

if [ ! -d "$DATA_DIR" ]; then
    echo "❌ No .decision_system/ directory found. Nothing to backup."
    exit 1
fi

# Determine output directory
if [ -n "${1:-}" ]; then
    OUT_DIR="$1"
else
    OUT_DIR="$DATA_DIR/backups"
fi
mkdir -p "$OUT_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$OUT_DIR/decision_system_backup_$TIMESTAMP.tar.gz"

echo "============================================"
echo "  Backup — Agentic Decision System"
echo "============================================"
echo ""
echo "  Source: $DATA_DIR/"
echo "  Output: $BACKUP_FILE"
echo ""

# Estimate size
SIZE=$(du -sh "$DATA_DIR" 2>/dev/null | cut -f1)
echo "  Data size: $SIZE"

# Create backup
echo ""
echo "  Creating backup..."
tar czf "$BACKUP_FILE" \
    --exclude="$DATA_DIR/backups" \
    "$DATA_DIR/" 2>/dev/null

echo "  ✅ Backup created!"
echo "  File: $BACKUP_FILE"

# Show file size
BACKUP_SIZE=$(du -h "$BACKUP_FILE" 2>/dev/null | cut -f1)
echo "  Backup size: $BACKUP_SIZE"

echo ""
echo "  === Restore instructions ==="
echo ""
echo "  To restore from this backup:"
echo "    tar xzf $BACKUP_FILE -C /path/to/project"
echo ""
echo "  Or move it to restore later:"
echo "    mv $BACKUP_FILE .decision_system/backups/latest.tar.gz"
echo ""
