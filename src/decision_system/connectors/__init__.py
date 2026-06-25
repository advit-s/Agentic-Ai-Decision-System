"""Safe connector framework for controlled data intake (v1.28+).

Supports read-only connectors:
- Local Folder Connector (real)
- GitHub Repository Connector (real)
- URL / Web Page Import Connector (real)
- Notion, Google Drive (planned/disabled)

All connectors are read-only, workspace-scoped, audited, and locally stored.
"""

from decision_system.connectors.config_store import (
    ConnectorConfigStore,
    get_config_store,
    reset_config_store,
)
from decision_system.connectors.github_issues import (
    list_all_github_items,
    list_issues,
    list_pull_requests,
    list_releases,
)
from decision_system.connectors.models import (
    ConnectorCapability,
    ConnectorCitation,
    ConnectorConfig,
    ConnectorConfigStatus,
    ConnectorCredentialStatus,
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
    ConnectorTestDiagnostics,
    ConnectorType,
)
from decision_system.connectors.registry import (
    ConnectorRegistry,
    get_connector_definition,
    get_credential_status,
    get_registry,
    list_connectors,
    list_connectors_with_schemas,
)
from decision_system.connectors.runtime import (
    ConnectorRuntime,
    FakeConnectorRuntime,
)
from decision_system.connectors.setup_schemas import (
    ConnectorSetupSchema,
    SetupField,
    get_setup_schema,
    list_setup_schemas,
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
    "ConnectorCitation",
    "ConnectorConfig",
    "ConnectorConfigStatus",
    "ConnectorCredentialStatus",
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
    "ConnectorTestDiagnostics",
    "ConnectorType",
    # Registry
    "ConnectorRegistry",
    "get_connector_definition",
    "get_registry",
    "list_connectors",
    "list_connectors_with_schemas",
    "get_credential_status",
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
    # Setup schemas (v1.30)
    "ConnectorSetupSchema",
    "SetupField",
    "get_setup_schema",
    "list_setup_schemas",
    # GitHub issues (v1.30)
    "list_issues",
    "list_pull_requests",
    "list_releases",
    "list_all_github_items",
]
