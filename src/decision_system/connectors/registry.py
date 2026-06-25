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
        status=ConnectorStatus.STUB,
        description=(
            "Read-only Notion page/database import. "
            "Requires NOTION_API_KEY env var. "
            "Currently planned for a future milestone."
        ),
        capabilities=[ConnectorCapability.LIST, ConnectorCapability.IMPORT],
        requires_secrets=True,
        supports_dry_run=False,
        supports_import=True,
        supports_list=True,
        supports_test=True,
        is_stub=True,
    ),
    ConnectorDefinition(
        connector_id="google-drive",
        name="Google Drive",
        connector_type=ConnectorType.GOOGLE_DRIVE,
        status=ConnectorStatus.STUB,
        description=(
            "Read-only Google Drive file import. "
            "Requires GOOGLE_DRIVE_TOKEN or GOOGLE_APPLICATION_CREDENTIALS env var. "
            "Currently planned for a future milestone."
        ),
        capabilities=[ConnectorCapability.LIST, ConnectorCapability.IMPORT],
        requires_secrets=True,
        supports_dry_run=False,
        supports_import=True,
        supports_list=True,
        supports_test=True,
        is_stub=True,
    ),
]


class ConnectorRegistry:
    """In-memory registry of connector definitions."""

    def __init__(self, connectors: list[ConnectorDefinition] | None = None) -> None:
        source = connectors if connectors is not None else _BUILTIN_CONNECTORS
        self._connectors: dict[str, ConnectorDefinition] = {c.connector_id: c for c in source}

    def list_connectors(self) -> list[ConnectorDefinition]:
        """Return all registered connector definitions."""
        return list(self._connectors.values())

    def get_definition(self, connector_id: str) -> ConnectorDefinition | None:
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


def get_connector_with_schema(connector_id: str) -> dict | None:
    """Return a connector definition merged with its setup schema, or None."""
    from decision_system.connectors.setup_schemas import get_setup_schema

    definition = get_connector_definition(connector_id)
    if definition is None:
        return None
    schema = get_setup_schema(connector_id)
    result = definition.model_dump(mode="json")
    result["setup_schema"] = schema.model_dump(mode="json") if schema else None
    return result


def list_connectors_with_schemas() -> list[dict]:
    """Return all connector definitions merged with setup schemas."""
    result = []
    for c in list_connectors():
        merged = get_connector_with_schema(c.connector_id)
        if merged:
            result.append(merged)
    return result


def get_credential_status(connector_id: str) -> dict | None:
    """Return safe credential status for a connector, or None if unknown."""
    from decision_system.connectors.setup_schemas import get_setup_schema

    schema = get_setup_schema(connector_id)
    if schema is None:
        return None
    if not schema.credential_fields:
        return {
            "configured": True,
            "token_present": False,
            "env_var_name": "",
            "missing_message": "",
            "has_required": True,
        }
    import os

    all_present = True
    statuses = []
    for field in schema.credential_fields:
        env_name = field.env_var_hint
        token_present = bool(os.environ.get(env_name, ""))
        statuses.append(
            {
                "field": field.key,
                "label": field.label,
                "env_var_name": env_name,
                "token_present": token_present,
                "required": field.required,
            }
        )
        if field.required and not token_present:
            all_present = False
    return {
        "configured": all_present,
        "token_present": all_present,
        "has_required": all_present,
        "fields": statuses,
        "missing_message": (
            "Set the required environment variable(s) to enable authenticated access."
            if not all_present
            else ""
        ),
    }
