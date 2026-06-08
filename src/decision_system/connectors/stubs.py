"""Offline connector stubs for external integrations not yet implemented."""
from __future__ import annotations

from decision_system.connectors.models import (
    ConnectorDefinition,
    ConnectorDryRunResult,
    ConnectorImportJob,
    ConnectorImportResult,
    ConnectorStatus,
)
from decision_system.connectors.registry import ConnectorRegistry


class ExternalConnectorError(Exception):
    """Raised when a stub connector is asked to do something real."""


def run_stub_dry_run(
    connector_id: str,
    definition: ConnectorDefinition,
) -> ConnectorDryRunResult:
    """Return a dry-run failure for any stub connector."""
    return ConnectorDryRunResult(
        connector_id=connector_id,
        source_path="",
        files=[],
        skipped_files=[],
        warnings=[
            f"Connector '{connector_id}' ({definition.name}) is a stub "
            f"and does not support dry-run in v1.1."
        ],
        would_import_count=0,
    )


def run_stub_import(
    connector_id: str,
    definition: ConnectorDefinition,
) -> ConnectorImportResult:
    """Return an import failure for any stub connector."""
    raise ExternalConnectorError(
        f"Connector '{connector_id}' ({definition.name}) is a stub "
        f"and not implemented in v1.1. No external calls are made."
    )
