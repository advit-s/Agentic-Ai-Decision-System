"""Connector registry: discover, inspect, and dispatch connector operations."""

from __future__ import annotations

from decision_system.connectors.models import (
    ConnectorCapability,
    ConnectorDefinition,
    ConnectorStatus,
    ConnectorType,
)

_BUILTIN_CONNECTORS: list[ConnectorDefinition] = [
    ConnectorDefinition(
        connector_id="local-files",
        name="Local Files",
        connector_type=ConnectorType.LOCAL_FILES,
        status=ConnectorStatus.REAL,
        description=(
            "Import safe local files (md, txt, csv, json) into generated "
            "connector import folders with dry-run and audit trail support."
        ),
        capabilities=[
            ConnectorCapability.DRY_RUN,
            ConnectorCapability.IMPORT,
            ConnectorCapability.LIST,
            ConnectorCapability.INSPECT,
            ConnectorCapability.TEST,
        ],
        requires_secrets=False,
        supports_dry_run=True,
        supports_import=True,
        supports_list=True,
        supports_test=True,
        is_stub=False,
    ),
    ConnectorDefinition(
        connector_id="github",
        name="GitHub Repository",
        connector_type=ConnectorType.GITHUB,
        status=ConnectorStatus.REAL,
        description=(
            "Read-only import of public GitHub repository files. "
            "Optional token via GITHUB_TOKEN env var for rate-limit increases. "
            "Lists repo files and imports selected files as local data sources."
        ),
        capabilities=[
            ConnectorCapability.LIST,
            ConnectorCapability.IMPORT,
            ConnectorCapability.TEST,
            ConnectorCapability.INSPECT,
        ],
        requires_secrets=False,
        supports_dry_run=False,
        supports_import=True,
        supports_list=True,
        supports_test=True,
        is_stub=False,
    ),
    ConnectorDefinition(
        connector_id="url-import",
        name="URL / Web Page Import",
        connector_type=ConnectorType.URL_IMPORT,
        status=ConnectorStatus.REAL,
        description=(
            "Import a single URL or web page as a local data source. "
            "Extracts title and text content from HTML pages. "
            "Blocks private/internal network addresses by default."
        ),
        capabilities=[
            ConnectorCapability.IMPORT,
            ConnectorCapability.TEST,
            ConnectorCapability.INSPECT,
        ],
        requires_secrets=False,
        supports_dry_run=False,
        supports_import=True,
        supports_list=False,
        supports_test=True,
        is_stub=False,
    ),
    ConnectorDefinition(
        connector_id="notion",
        name="Notion",
        connector_type=ConnectorType.NOTION,
        status=ConnectorStatus.UNAVAILABLE,
        description="Notion read-only connector (not implemented in v1.28).",
        capabilities=[],
        requires_secrets=True,
        supports_dry_run=False,
        supports_import=False,
        supports_list=False,
        supports_test=False,
        is_stub=True,
    ),
    ConnectorDefinition(
        connector_id="google-drive",
        name="Google Drive",
        connector_type=ConnectorType.GOOGLE_DRIVE,
        status=ConnectorStatus.UNAVAILABLE,
        description="Google Drive read-only connector (not implemented in v1.28).",
        capabilities=[],
        requires_secrets=True,
        supports_dry_run=False,
        supports_import=False,
        supports_list=False,
        supports_test=False,
        is_stub=True,
    ),
]


class ConnectorRegistry:
    """In-memory registry of connector definitions."""

    def __init__(
        self, connectors: list[ConnectorDefinition] | None = None
    ) -> None:
        source = connectors if connectors is not None else _BUILTIN_CONNECTORS
        self._connectors: dict[str, ConnectorDefinition] = {
            c.connector_id: c for c in source
        }

    def list_connectors(self) -> list[ConnectorDefinition]:
        """Return all registered connector definitions."""
        return list(self._connectors.values())

    def get_definition(
        self, connector_id: str
    ) -> ConnectorDefinition | None:
        """Return a connector definition by id, or None if unregistered."""
        return self._connectors.get(connector_id)

    def is_stub(self, connector_id: str) -> bool:
        """Return True when the connector is a stub (not a real integration)."""
        definition = self._connectors.get(connector_id)
        return bool(definition and definition.is_stub)


# Module-level singleton
_registry_inst = ConnectorRegistry()


def get_registry() -> ConnectorRegistry:
    """Return the shared connector registry singleton."""
    return _registry_inst


def list_connectors() -> list[ConnectorDefinition]:
    """Return all registered connector definitions."""
    return get_registry().list_connectors()


def get_connector_definition(
    connector_id: str,
) -> ConnectorDefinition | None:
    """Return a connector definition by id, or None if not registered."""
    return get_registry().get_definition(connector_id)
