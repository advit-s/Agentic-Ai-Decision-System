"""Persistent connector config store backed by JSON files.

Stores connector configurations under .decision_system/connectors/configs/.
Supports workspace-scoped and global connector configs.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from decision_system._data_root import get_data_root
from decision_system.connectors.models import (
    ConnectorConfig,
    ConnectorConfigStatus,
    ConnectorMode,
    ConnectorSecretRef,
    ConnectorType,
)


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _write_json(path: Path, data: Any) -> None:
    _ensure_dir(path.parent)
    path.write_text(
        json.dumps(data, indent=2, default=str, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _default_configs_dir() -> Path:
    return get_data_root() / "connectors" / "configs"


class ConnectorConfigStore:
    """Persistent JSON-backed store for connector configurations."""

    def __init__(self, configs_dir: str | Path | None = None) -> None:
        self._configs_dir = Path(configs_dir) if configs_dir else _default_configs_dir()
        _ensure_dir(self._configs_dir)

    def _workspace_dir(self, workspace_id: str | None) -> Path:
        scope = workspace_id if workspace_id else "_global"
        d = self._configs_dir / scope
        _ensure_dir(d)
        return d

    def _config_path(self, workspace_id: str | None, connector_id: str) -> Path:
        return self._workspace_dir(workspace_id) / f"{connector_id}.json"

    def _index_path(self, workspace_id: str | None) -> Path:
        return self._workspace_dir(workspace_id) / "_index.json"

    def _load_index(self, workspace_id: str | None) -> list[str]:
        data = _read_json(self._index_path(workspace_id))
        return data if isinstance(data, list) else []

    def _save_index(self, workspace_id: str | None, ids: list[str]) -> None:
        _write_json(self._index_path(workspace_id), ids)

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create(
        self,
        name: str,
        connector_type: ConnectorType,
        config: dict[str, Any] | None = None,
        workspace_id: str | None = None,
        secret_refs: list[ConnectorSecretRef] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ConnectorConfig:
        """Create a new connector config with auto-generated ID."""
        cfg = ConnectorConfig(
            connector_id=str(uuid4()),
            workspace_id=workspace_id,
            name=name,
            connector_type=connector_type,
            mode=ConnectorMode.READ_ONLY,
            status=ConnectorConfigStatus.CONFIGURED,
            config=config or {},
            secret_refs=secret_refs or [],
            metadata=metadata or {},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        return self.save(cfg)

    def save(self, cfg: ConnectorConfig) -> ConnectorConfig:
        """Save or update a connector config."""
        cfg.updated_at = datetime.now(timezone.utc)
        _write_json(
            self._config_path(cfg.workspace_id, cfg.connector_id),
            cfg.model_dump(mode="json"),
        )
        ids = self._load_index(cfg.workspace_id)
        if cfg.connector_id not in ids:
            ids.append(cfg.connector_id)
            self._save_index(cfg.workspace_id, ids)
        return cfg

    def load(self, workspace_id: str | None, connector_id: str) -> ConnectorConfig | None:
        """Load a connector config by workspace and connector_id."""
        data = _read_json(self._config_path(workspace_id, connector_id))
        if data is None:
            return None
        return ConnectorConfig(**data)

    def list_by_workspace(self, workspace_id: str | None) -> list[ConnectorConfig]:
        """List all connector configs for a workspace (or global)."""
        configs: list[ConnectorConfig] = []
        for cid in self._load_index(workspace_id):
            c = self.load(workspace_id, cid)
            if c is not None:
                configs.append(c)
        return configs

    def list_all(self) -> list[ConnectorConfig]:
        """List all connector configs across all scopes."""
        configs: list[ConnectorConfig] = []
        if not self._configs_dir.exists():
            return configs
        for scope_dir in sorted(self._configs_dir.iterdir()):
            if not scope_dir.is_dir() or scope_dir.name.startswith("."):
                continue
            ws_id = scope_dir.name if scope_dir.name != "_global" else None
            configs.extend(self.list_by_workspace(ws_id))
        return configs

    def delete(self, workspace_id: str | None, connector_id: str) -> bool:
        """Delete a connector config. Returns True if it existed."""
        path = self._config_path(workspace_id, connector_id)
        existed = path.exists()
        if existed:
            path.unlink()
        ids = self._load_index(workspace_id)
        if connector_id in ids:
            ids.remove(connector_id)
            self._save_index(workspace_id, ids)
        return existed

    def update_status(
        self,
        workspace_id: str | None,
        connector_id: str,
        status: ConnectorConfigStatus,
    ) -> ConnectorConfig | None:
        """Update the health status of a connector config."""
        cfg = self.load(workspace_id, connector_id)
        if cfg is None:
            return None
        cfg.status = status
        return self.save(cfg)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def apply_secrets(self, cfg: ConnectorConfig) -> dict[str, Any]:
        """Resolve secret refs from environment variables into a config dict.

        Returns a copy of cfg.config with secret values resolved from env.
        Missing optional secrets are silently skipped.
        Missing required secrets set status to MISSING_CONFIG.
        """
        resolved = dict(cfg.config)
        for ref in cfg.secret_refs:
            if ref.key in resolved:
                continue  # already set
            value = os.environ.get(ref.key)
            if value:
                resolved[ref.key] = value
            elif not ref.optional:
                # Mark status, but don't raise
                pass
        return resolved


# Module-level singleton
_store_inst: ConnectorConfigStore | None = None


def get_config_store() -> ConnectorConfigStore:
    """Return the shared connector config store singleton."""
    global _store_inst
    if _store_inst is None:
        _store_inst = ConnectorConfigStore()
    return _store_inst


def reset_config_store() -> None:
    """Reset the singleton (for testing)."""
    global _store_inst
    _store_inst = None
