"""Safe connector framework for controlled data intake.

v1.1 only implements the local-files connector as a real operation.
GitHub, Jira, Slack, and Email connectors are offline stubs.
"""

from decision_system.connectors.models import (
    ConnectorCapability,
    ConnectorDefinition,
    ConnectorDryRunFile,
    ConnectorDryRunResult,
    ConnectorImportJob,
    ConnectorImportResult,
    ConnectorStatus,
    ConnectorType,
)
from decision_system.connectors.registry import (
    ConnectorRegistry,
    get_connector_definition,
    get_registry,
    list_connectors,
)
from decision_system.connectors.store import (
    ConnectorJobStore,
    append_job,
    delete_job,
    get_job,
    load_jobs,
    save_job,
)

__all__ = [
    # Models
    "ConnectorCapability",
    "ConnectorDefinition",
    "ConnectorDryRunFile",
    "ConnectorDryRunResult",
    "ConnectorImportJob",
    "ConnectorImportResult",
    "ConnectorStatus",
    "ConnectorType",
    # Registry
    "ConnectorRegistry",
    "get_connector_definition",
    "get_registry",
    "list_connectors",
    # Store
    "ConnectorJobStore",
    "append_job",
    "delete_job",
    "get_job",
    "load_jobs",
    "save_job",
]
