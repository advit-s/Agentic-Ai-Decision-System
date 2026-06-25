# Migration & Upgrade Guide

> **Last updated**: 2026-06-25

This document describes how to migrate between major versions of the Agentic Decision System.

## Version Compatibility

| From | To | Breaking Changes | Migration Steps |
|------|----|-----------------|-----------------|
| v1.34.x | v1.35.0 | Path resolution changes | See below |
| v1.33.x | v1.34.0 | None | Restart services |
| v1.32.x | v1.33.0 | None | Restart services |
| v1.31.x | v1.32.0 | None | `pip install -e ".[dev]"` |
| v1.30.x | v1.31.0 | None | `pip install -e ".[dev]"` |
| v1.29.x | v1.30.0 | Claim store format | See v1.30 notes |
| v1.28.x | v1.29.0 | None | `pip install -e ".[dev]"` |

## v1.34 → v1.35 (Path Resolution Changes)

**What changed**: Module-level `get_data_root()` calls were converted to lazy evaluation
functions. This affects any custom code that depends on `DEFAULT_*` path constants.

**Migration**:
```python
# OLD (v1.34 and earlier)
from decision_system.graphing.store import DEFAULT_GRAPH_PATH

# NEW (v1.35+)
from decision_system._data_root import get_data_root
# Call get_data_root() at function call time, not import time
```

**Data directory**: The `DECISION_SYSTEM_DATA_DIR` environment variable controls
the data root. When unset, it defaults to `.decision_system/` in the current
working directory.

**Workspace database**: The `DECISION_WORKSPACE_DB` environment variable controls
the workspace SQLite database path. When unset, it defaults to
`.decision_system/workspaces/workspaces.sqlite`.

**Security settings**: Security mode configuration is stored at
`.decision_system/identity/security_settings.json`.

## General Upgrade Procedure

1. **Back up your data**:
   ```bash
   bash scripts/backup-local-data.sh
   ```

2. **Pull the latest code**:
   ```bash
   git pull origin main
   ```

3. **Update Python dependencies**:
   ```bash
   source .venv/bin/activate
   python -m pip install -e ".[dev]"
   ```

4. **Update frontend dependencies** (if using SPA):
   ```bash
   cd web/workflow-builder && npm install && npm run build
   ```

5. **Run the test suite**:
   ```bash
   python -m pytest -q
   ```

6. **Restart services**:
   ```bash
   # Docker
   docker compose down && docker compose up --build

   # Local
   bash scripts/stop-local.sh && bash scripts/start-local.sh
   ```

## Rollback

If an upgrade fails, restore from backup:

```bash
# Restore data from the most recent backup
tar -xzf backups/decision-data-*.tar.gz -C /path/to/restore
```

## Data Format Stability

The following storage formats are considered stable within a major version:
- Workspace SQLite database (`.decision_system/workspaces/workspaces.sqlite`)
- Chroma vector store (`.decision_system/chroma/`)
- Security settings JSON (`.decision_system/identity/security_settings.json`)
- Report exports (`.decision_system/workspaces/exports/*.json`)

The following are considered internal and may change without notice:
- Knowledge graph store internals
- Claim ledger JSONL format
- Audit log JSONL format
- Provider configuration
- Data source chunk stores
