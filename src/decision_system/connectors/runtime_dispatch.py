"""Connector runtime dispatch — maps connector types to runtime implementations.

Provides a unified interface for test_connection, list_items, fetch_item, and sync
across all connector types. The dispatch falls back to the v1.1 local-files
implementation for backward compatibility.
"""

from __future__ import annotations

from typing import Any

from datetime import datetime, timezone
from decision_system.connectors.models import (
    ConnectorConfig,
    ConnectorFetchedContent,
    ConnectorRuntimeItem,
    ConnectorTestDiagnostics,
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
        runtime = FakeConnectorRuntime(
            connector_id="notion",
            label="Notion",
        )
    elif connector_type == ConnectorType.GOOGLE_DRIVE:
        runtime = FakeConnectorRuntime(
            connector_id="google-drive",
            label="Google Drive",
        )
    else:
        raise ValueError(f"Unknown connector type: {connector_type}")

    _runtimes[key] = runtime
    return runtime


def test_connection(config: ConnectorConfig) -> dict[str, Any]:
    """Test connectivity for a connector config."""
    from decision_system.connectors.registry import get_credential_status
    from decision_system.security.redaction import redact_connector_token

    runtime = _get_runtime(config.connector_type)
    result = runtime.test_connection(config)

    # Safely redact any token values from the result
    safe_result = {}
    for k, v in result.items():
        if isinstance(v, str):
            safe_result[k] = redact_connector_token(v)
        else:
            safe_result[k] = v

    # Build structured diagnostics
    cred_status = get_credential_status(config.connector_type.value)
    success = safe_result.get("success", False)

    diagnostics = ConnectorTestDiagnostics(
        status="success" if success else "error",
        message=safe_result.get("message", "Test completed"),
        checked_at=datetime.now(timezone.utc).isoformat(),
        connector_type=config.connector_type.value,
        reachable=success,
        auth_configured=cred_status.get("has_required", False) if cred_status else True,
        permissions_summary=safe_result.get("message", ""),
        warnings=safe_result.get("warnings", []),
        errors=safe_result.get("errors", []),
    )

    diag_dict = diagnostics.model_dump(mode="json")
    # Include legacy keys for backward compatibility
    diag_dict["success"] = success
    if "message" in safe_result:
        diag_dict["message"] = safe_result["message"]

    return diag_dict


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
