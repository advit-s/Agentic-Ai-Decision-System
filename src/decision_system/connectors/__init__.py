"""Safe connector framework for controlled data intake (v1.28).

Supports read-only connectors:
- Local Folder Connector (real)
- GitHub Repository Connector (real)
- URL / Web Page Import Connector (real)
- Notion, Google Drive (unavailable in v1.28)

All connectors are read-only, workspace-scoped, audited, and locally stored.
"""

from decision_system.connectors.models import (
    ConnectorCapability,
    ConnectorCitation,
    ConnectorConfig,
    ConnectorConfigStatus,
    ConnectorDefinition,
    ConnectorDryRunFile,
    ConnectorDryRunResult,
    ConnectorFetchedContent,
    ConnectorImportJob,
    ConnectorImportResult,
    ConnectorMode,
    ConnectorRuntimeItem,
    ConnectorSecretRef,
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
from decision_system.connectors.config_store import (
    ConnectorConfigStore,
    get_config_store,
    reset_config_store,
)
from decision_system.connectors.runtime import (
    ConnectorRuntime,
    FakeConnectorRuntime,
)

__all__ = [
    # Models
    "ConnectorCapability",
    "ConnectorCitation",
    "ConnectorConfig",
    "ConnectorConfigStatus",
    "ConnectorDefinition",
    "ConnectorDryRunFile",
    "ConnectorDryRunResult",
    "ConnectorFetchedContent",
    "ConnectorImportJob",
    "ConnectorImportResult",
    "ConnectorMode",
    "ConnectorRuntimeItem",
    "ConnectorSecretRef",
    "ConnectorStatus",
    "ConnectorType",
    # Registry
    "ConnectorRegistry",
    "get_connector_definition",
    "get_registry",
    "list_connectors",
    # Store (jobs)
    "ConnectorJobStore",
    "append_job",
    "delete_job",
    "get_job",
    "load_jobs",
    "save_job",
    # Config store
    "ConnectorConfigStore",
    "get_config_store",
    "reset_config_store",
    # Runtime
    "ConnectorRuntime",
    "FakeConnectorRuntime",
]
