"""Connector setup schemas — standardized setup metadata per connector type.

Each connector type defines its setup schema so the frontend can render
dynamic configuration forms, validate inputs, and guide users through
credential setup.

v1.30 — Connector Expansion + OAuth/Token Setup UX
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class FieldType(StrEnum):
    """Input field types for connector setup forms."""
    STRING = "string"
    PASSWORD = "password"
    URL = "url"
    PATH = "path"
    NUMBER = "number"
    BOOLEAN = "boolean"
    SELECT = "select"


class SetupField(BaseModel):
    """A single field in a connector setup form."""
    key: str = Field(description="Field identifier (snake_case)")
    label: str = Field(description="Human-readable label")
    field_type: FieldType = Field(default=FieldType.STRING, description="Input type")
    required: bool = Field(default=False, description="Whether the field is required")
    placeholder: str = Field(default="", description="Placeholder text")
    hint: str = Field(default="", description="Help text shown below the field")
    default_value: str | None = Field(default=None, description="Default value")
    options: list[str] = Field(default_factory=list, description="For SELECT type")
    secret: bool = Field(default=False, description="True if this field holds a secret/token")
    env_var_hint: str = Field(default="", description="Recommended env-var name, e.g. GITHUB_TOKEN")
    validation_pattern: str | None = Field(default=None, description="Regex pattern for validation")


class ConnectorCapabilityDetail(BaseModel):
    """Description of a single read-only capability."""
    capability: str = Field(description="Capability identifier")
    label: str = Field(description="Human-readable label")
    description: str = Field(description="What this capability allows")
    read_only: bool = Field(default=True, description="Always true for safety")


class ConnectorSetupSchema(BaseModel):
    """Complete setup schema for a connector type.
    
    Frontends use this to render dynamic configuration forms with
    appropriate field types, validation, and credential guidance.
    """
    connector_type: str = Field(description="Connector type identifier")
    display_name: str = Field(description="Human-readable name")
    description: str = Field(description="What this connector does")
    read_only_capabilities: list[ConnectorCapabilityDetail] = Field(
        default_factory=list,
        description="What the connector can read (all read-only)",
    )
    required_fields: list[SetupField] = Field(
        default_factory=list,
        description="Fields the user must fill in",
    )
    optional_fields: list[SetupField] = Field(
        default_factory=list,
        description="Optional configuration fields",
    )
    credential_fields: list[SetupField] = Field(
        default_factory=list,
        description="Credential/token fields (always stored as env-var refs)",
    )
    env_var_hints: list[str] = Field(
        default_factory=list,
        description="Recommended environment variable names",
    )
    safety_notes: list[str] = Field(
        default_factory=list,
        description="Safety warnings for this connector",
    )
    supported_item_types: list[str] = Field(
        default_factory=list,
        description="Types of items this connector can import",
    )
    default_sync_behavior: str = Field(
        default="manual",
        description="Default sync mode: manual, scheduled, or both",
    )
    disabled: bool = Field(
        default=False,
        description="True if this connector is planned but not implemented",
    )
    disabled_reason: str = Field(
        default="",
        description="Why this connector is disabled (if disabled=True)",
    )


def _rw(description: str) -> str:
    """Tag a capability description as read-only."""
    return f"{description} (read-only)"


# ---------------------------------------------------------------------------
# Built-in connector setup schemas
# ---------------------------------------------------------------------------

LOCAL_FILES_SCHEMA = ConnectorSetupSchema(
    connector_type="local-files",
    display_name="Local Folder",
    description="Import safe local files (markdown, text, CSV, JSON) from a folder on your machine.",
    read_only_capabilities=[
        ConnectorCapabilityDetail(
            capability="list",
            label="List Files",
            description=_rw("Scan a local folder and list supported files"),
        ),
        ConnectorCapabilityDetail(
            capability="import",
            label="Import Files",
            description=_rw("Copy selected files into the workspace as read-only data sources"),
        ),
        ConnectorCapabilityDetail(
            capability="test",
            label="Test Connection",
            description=_rw("Verify the folder path exists and is readable"),
        ),
    ],
    required_fields=[
        SetupField(
            key="folder_path",
            label="Folder Path",
            field_type=FieldType.PATH,
            required=True,
            placeholder="/home/user/documents",
            hint="Absolute path to the folder containing your files.",
            validation_pattern=r"^/",
        ),
    ],
    optional_fields=[],
    credential_fields=[],
    env_var_hints=[],
    safety_notes=[
        "Only files with supported extensions (.md, .txt, .csv, .json, .yml, .xml, .html) are imported.",
        "System directories and hidden files are excluded.",
        "Files are copied into the workspace; original files are never modified.",
    ],
    supported_item_types=["markdown", "text", "csv", "json", "yaml", "xml", "html"],
    default_sync_behavior="manual",
)

GITHUB_SCHEMA = ConnectorSetupSchema(
    connector_type="github",
    display_name="GitHub Repository",
    description="Read-only import of files, issues, and pull requests from a public GitHub repository.",
    read_only_capabilities=[
        ConnectorCapabilityDetail(
            capability="list",
            label="List Repository Files",
            description=_rw("List files and folders from a public GitHub repository"),
        ),
        ConnectorCapabilityDetail(
            capability="import",
            label="Import Files",
            description=_rw("Fetch selected file contents and store them locally"),
        ),
        ConnectorCapabilityDetail(
            capability="test",
            label="Test Connection",
            description=_rw("Verify the repository URL is accessible via the GitHub API"),
        ),
    ],
    required_fields=[
        SetupField(
            key="repository_url",
            label="Repository URL",
            field_type=FieldType.URL,
            required=True,
            placeholder="https://github.com/owner/repo",
            hint="Full URL to a public GitHub repository.",
            validation_pattern=r"^https://github\.com/",
        ),
    ],
    optional_fields=[],
    credential_fields=[
        SetupField(
            key="github_token",
            label="GitHub Token",
            field_type=FieldType.PASSWORD,
            required=False,
            placeholder="GITHUB_TOKEN",
            hint="Optional. Set the GITHUB_TOKEN environment variable for higher API rate limits or private repos.",
            secret=True,
            env_var_hint="GITHUB_TOKEN",
        ),
    ],
    env_var_hints=["GITHUB_TOKEN"],
    safety_notes=[
        "All operations are read-only. No commits, issues, PRs, or comments are created.",
        "Public repositories do not require a token. A token only increases rate limits.",
        "Token values are never stored in the connector config or returned from the API.",
        "Set GITHUB_TOKEN as an environment variable before starting the application.",
    ],
    supported_item_types=["file", "issue", "pull_request", "release"],
    default_sync_behavior="manual",
)

URL_IMPORT_SCHEMA = ConnectorSetupSchema(
    connector_type="url-import",
    display_name="URL / Web Page Import",
    description="Import a single web page as a local data source. Extracts title and text content.",
    read_only_capabilities=[
        ConnectorCapabilityDetail(
            capability="import",
            label="Import Web Page",
            description=_rw("Fetch a URL and store its content locally"),
        ),
        ConnectorCapabilityDetail(
            capability="test",
            label="Test Connection",
            description=_rw("Verify the URL is reachable and returns HTML content"),
        ),
    ],
    required_fields=[
        SetupField(
            key="url",
            label="Web Page URL",
            field_type=FieldType.URL,
            required=True,
            placeholder="https://example.com/page",
            hint="Full URL to the web page you want to import.",
        ),
    ],
    optional_fields=[],
    credential_fields=[],
    env_var_hints=[],
    safety_notes=[
        "Only HTTP GET requests are made. No data is sent to the target server.",
        "Private and internal network addresses (10.x.x.x, 172.x.x.x, 192.168.x.x, localhost) are blocked.",
        "Response size is limited to 10 MB.",
        "Only HTML pages are imported; non-HTML content types are rejected.",
    ],
    supported_item_types=["html_page"],
    default_sync_behavior="manual",
)

NOTION_SCHEMA = ConnectorSetupSchema(
    connector_type="notion",
    display_name="Notion",
    description="Read-only import of Notion pages and databases. (Planned for future milestone.)",
    read_only_capabilities=[
        ConnectorCapabilityDetail(
            capability="list",
            label="List Pages/Databases",
            description=_rw("List accessible Notion pages and databases (planned)"),
        ),
        ConnectorCapabilityDetail(
            capability="import",
            label="Import Pages",
            description=_rw("Fetch Notion page content and store locally (planned)"),
        ),
    ],
    required_fields=[],
    optional_fields=[],
    credential_fields=[
        SetupField(
            key="notion_api_key",
            label="Notion API Key",
            field_type=FieldType.PASSWORD,
            required=True,
            placeholder="NOTION_API_KEY",
            hint="Set the NOTION_API_KEY environment variable with your Notion integration token.",
            secret=True,
            env_var_hint="NOTION_API_KEY",
        ),
    ],
    env_var_hints=["NOTION_API_KEY"],
    safety_notes=[
        "Notion import is read-only. No pages, databases, or content are created or modified.",
        "Requires a Notion integration token with read capabilities.",
        "Token values are never stored in the connector config or returned from the API.",
    ],
    supported_item_types=["page", "database"],
    default_sync_behavior="manual",
    disabled=True,
    disabled_reason="Notion read-only import requires a Notion integration and is planned for a future milestone.",
)

GOOGLE_DRIVE_SCHEMA = ConnectorSetupSchema(
    connector_type="google-drive",
    display_name="Google Drive",
    description="Read-only import of Google Drive files. (Planned for future milestone.)",
    read_only_capabilities=[
        ConnectorCapabilityDetail(
            capability="list",
            label="List Files",
            description=_rw("List accessible Google Drive files (planned)"),
        ),
        ConnectorCapabilityDetail(
            capability="import",
            label="Import Files",
            description=_rw("Fetch Google Drive file content and store locally (planned)"),
        ),
    ],
    required_fields=[],
    optional_fields=[],
    credential_fields=[
        SetupField(
            key="google_drive_credentials",
            label="Google Drive Credentials",
            field_type=FieldType.PASSWORD,
            required=True,
            placeholder="GOOGLE_DRIVE_TOKEN or GOOGLE_APPLICATION_CREDENTIALS",
            hint="Set GOOGLE_DRIVE_TOKEN or GOOGLE_APPLICATION_CREDENTIALS environment variable.",
            secret=True,
            env_var_hint="GOOGLE_DRIVE_TOKEN",
        ),
    ],
    env_var_hints=["GOOGLE_DRIVE_TOKEN", "GOOGLE_APPLICATION_CREDENTIALS"],
    safety_notes=[
        "Google Drive import is read-only. No files are created or modified.",
        "Requires a Google API token or application credentials with read scope.",
        "Token values are never stored in the connector config or returned from the API.",
    ],
    supported_item_types=["document", "spreadsheet", "pdf", "text"],
    default_sync_behavior="manual",
    disabled=True,
    disabled_reason="Google Drive read-only import requires OAuth setup and is planned for a future milestone.",
)


# ---------------------------------------------------------------------------
# Registry of all built-in schemas
# ---------------------------------------------------------------------------

_BUILTIN_SCHEMAS: dict[str, ConnectorSetupSchema] = {
    "local-files": LOCAL_FILES_SCHEMA,
    "github": GITHUB_SCHEMA,
    "url-import": URL_IMPORT_SCHEMA,
    "notion": NOTION_SCHEMA,
    "google-drive": GOOGLE_DRIVE_SCHEMA,
}


def get_setup_schema(connector_type: str) -> ConnectorSetupSchema | None:
    """Return the setup schema for a connector type, or None if unknown."""
    return _BUILTIN_SCHEMAS.get(connector_type)


def list_setup_schemas() -> list[ConnectorSetupSchema]:
    """Return all built-in connector setup schemas."""
    return list(_BUILTIN_SCHEMAS.values())
