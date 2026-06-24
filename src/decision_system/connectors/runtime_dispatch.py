"""Connector runtime dispatch — maps connector types to runtime implementations.

Provides a unified interface for test_connection, list_items, fetch_item, and sync
across all connector types. The dispatch falls back to the v1.1 local-files
implementation for backward compatibility.
"""

from __future__ import annotations

from typing import Any

from decision_system.connectors.models import (
    ConnectorConfig,
    ConnectorRuntimeItem,
    ConnectorFetchedContent,
    ConnectorType,
)
from decision_system.connectors.runtime import (
    ConnectorRuntime,
    FakeConnectorRuntime,
)
from decision_system.connectors.github_connector import get_github_connector
from decision_system.connectors.url_connector import get_url_connector
from decision_system.connectors.local_files import LocalFolderConnectorRuntime


# Runtime cache
_runtimes: dict[str, ConnectorRuntime] = {}


def _get_runtime(connector_type: ConnectorType) -> ConnectorRuntime:
    """Get or create a runtime implementation for the given connector type."""
    key = connector_type.value
    if key in _runtimes:
        return _runtimes[key]

    if connector_type == ConnectorType.GITHUB:
        runtime = get_github_connector()
    elif connector_type == ConnectorType.URL_IMPORT:
        runtime = get_url_connector()
    elif connector_type == ConnectorType.LOCAL_FILES:
        runtime = LocalFolderConnectorRuntime()
    elif connector_type == ConnectorType.NOTION:
        raise NotImplementedError("Notion connector not available in v1.28")
    elif connector_type == ConnectorType.GOOGLE_DRIVE:
        raise NotImplementedError("Google Drive connector not available in v1.28")
    else:
        raise ValueError(f"Unknown connector type: {connector_type}")

    _runtimes[key] = runtime
    return runtime


def test_connection(config: ConnectorConfig) -> dict[str, Any]:
    """Test connectivity for a connector config."""
    runtime = _get_runtime(config.connector_type)
    return runtime.test_connection(config)


def list_items(
    config: ConnectorConfig, path: str = ""
) -> list[ConnectorRuntimeItem]:
    """List items from a connector config."""
    runtime = _get_runtime(config.connector_type)
    return runtime.list_items(config, path)


def fetch_item(
    config: ConnectorConfig, item: ConnectorRuntimeItem
) -> ConnectorFetchedContent:
    """Fetch a single item from a connector config."""
    runtime = _get_runtime(config.connector_type)
    return runtime.fetch_item(config, item)


def sync(
    config: ConnectorConfig,
    path: str = "",
    item_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Run a full sync for a connector config."""
    runtime = _get_runtime(config.connector_type)
    return runtime.sync(config, path, item_ids)


def clear_runtime_cache() -> None:
    """Clear the runtime cache (for testing)."""
    _runtimes.clear()
