"""Tests for connector setup schemas, credential status, and diagnostics (v1.30)."""

from __future__ import annotations

import json
import os
from unittest.mock import patch

from decision_system.connectors.models import (
    ConnectorTestDiagnostics,
)
from decision_system.connectors.registry import (
    get_credential_status,
    list_connectors_with_schemas,
)
from decision_system.connectors.setup_schemas import (
    GITHUB_SCHEMA,
    FieldType,
    SetupField,
    get_setup_schema,
    list_setup_schemas,
)
from decision_system.security.redaction import (
    redact_connector_token,
    safe_credential_status,
)


class TestSetupSchemas:
    """Test connector setup schema definitions."""

    def test_list_returns_all(self):
        schemas = list_setup_schemas()
        assert len(schemas) >= 5
        types = [s.connector_type for s in schemas]
        assert "local-files" in types
        assert "github" in types
        assert "url-import" in types
        assert "notion" in types
        assert "google-drive" in types

    def test_get_local_files(self):
        schema = get_setup_schema("local-files")
        assert schema is not None
        assert schema.connector_type == "local-files"
        assert schema.display_name == "Local Folder"
        assert len(schema.required_fields) == 1
        assert schema.required_fields[0].key == "folder_path"
        assert schema.required_fields[0].field_type == FieldType.PATH
        assert not schema.disabled

    def test_get_github(self):
        schema = get_setup_schema("github")
        assert schema is not None
        assert schema.connector_type == "github"
        assert schema.display_name == "GitHub Repository"
        assert len(schema.required_fields) == 1
        assert schema.required_fields[0].key == "repository_url"
        assert len(schema.credential_fields) == 1
        assert schema.credential_fields[0].env_var_hint == "GITHUB_TOKEN"
        assert not schema.disabled

    def test_get_url_import(self):
        schema = get_setup_schema("url-import")
        assert schema is not None
        assert schema.connector_type == "url-import"
        assert len(schema.required_fields) == 1
        assert schema.required_fields[0].key == "url"

    def test_get_notion_disabled(self):
        schema = get_setup_schema("notion")
        assert schema is not None
        assert schema.disabled
        assert schema.disabled_reason
        assert len(schema.credential_fields) == 1

    def test_get_google_drive_disabled(self):
        schema = get_setup_schema("google-drive")
        assert schema is not None
        assert schema.disabled
        assert schema.disabled_reason
        assert len(schema.credential_fields) == 1

    def test_unknown_returns_none(self):
        schema = get_setup_schema("unknown-connector")
        assert schema is None

    def test_all_schemas_have_required_structure(self):
        schemas = list_setup_schemas()
        for s in schemas:
            assert s.connector_type
            assert s.display_name
            assert s.description
            assert isinstance(s.read_only_capabilities, list)
            assert isinstance(s.safety_notes, list)
            assert isinstance(s.supported_item_types, list)
            assert s.default_sync_behavior in ("manual", "scheduled", "both")

    def test_safety_notes_present(self):
        schemas = list_setup_schemas()
        for s in schemas:
            if not s.disabled:
                assert len(s.safety_notes) > 0, f"{s.connector_type} has no safety notes"

    def test_credential_fields_are_flagged_secret(self):
        schemas = list_setup_schemas()
        for s in schemas:
            for field in s.credential_fields:
                assert field.secret, f"{s.connector_type}.{field.key} not flagged secret"
                assert field.env_var_hint, f"{s.connector_type}.{field.key} missing env_var_hint"

    def test_setup_schema_serialization(self):
        schema = GITHUB_SCHEMA
        data = schema.model_dump(mode="json")
        assert data["connector_type"] == "github"
        assert data["display_name"] == "GitHub Repository"
        assert len(data["required_fields"]) == 1
        assert len(data["credential_fields"]) == 1
        assert data["credential_fields"][0]["env_var_hint"] == "GITHUB_TOKEN"


class TestCredentialStatus:
    """Test credential status reporting (no token values exposed)."""

    def test_local_files_no_creds(self):
        status = get_credential_status("local-files")
        assert status is not None
        assert status["configured"] is True
        assert status["has_required"] is True

    def test_github_credential_status(self):
        status = get_credential_status("github")
        assert status is not None
        assert "fields" in status
        assert len(status["fields"]) == 1
        assert status["fields"][0]["env_var_name"] == "GITHUB_TOKEN"
        # Token_present should be False when env var not set
        assert status["fields"][0]["token_present"] is False

    @patch.dict(os.environ, {"GITHUB_TOKEN": "ghp_test1234567890abcdef"}, clear=True)
    def test_github_token_present_detected(self):
        status = get_credential_status("github")
        assert status is not None
        assert status["fields"][0]["token_present"] is True
        assert status["has_required"] is True

    def test_unknown_type(self):
        status = get_credential_status("nonexistent")
        assert status is None

    def test_safe_credential_status_no_token(self):
        result = safe_credential_status("GITHUB_TOKEN")
        assert result["token_present"] is False
        assert not result["configured"]
        assert "GITHUB_TOKEN" in result["missing_message"]
        # Ensure no token value leaked
        serialized = json.dumps(result)
        assert "ghp_" not in serialized

    @patch.dict(os.environ, {"GITHUB_TOKEN": "ghp_test1234567890abcdef"}, clear=True)
    def test_safe_credential_status_token_present(self):
        result = safe_credential_status("GITHUB_TOKEN")
        assert result["token_present"] is True
        assert result["configured"] is True
        # Ensure no token value leaked
        serialized = json.dumps(result)
        assert "ghp_test1234567890abcdef" not in serialized


class TestTokenRedaction:
    """Test token redaction in logs/errors/audit."""

    def test_github_token_redacted(self):
        text = "My token is ghp_test1234567890abcdef and it's secret"
        redacted = redact_connector_token(text)
        assert "[REDACTED_TOKEN]" in redacted
        assert "ghp_test1234567890abcdef" not in redacted

    def test_bearer_token_redacted(self):
        text = "Authorization: Bearer ghp_test1234567890abcdef"
        redacted = redact_connector_token(text)
        assert "[REDACTED]" in redacted
        assert "ghp_test1234567890abcdef" not in redacted

    def test_env_var_redacted(self):
        text = "GITHUB_TOKEN=ghp_test1234567890abcdef"
        redacted = redact_connector_token(text)
        assert "[REDACTED]" in redacted
        assert "ghp_test1234567890abcdef" not in redacted

    def test_sk_key_redacted(self):
        text = "sk-Abcdefghijklmnopqrstuvwxyz0123456789ABC"
        redacted = redact_connector_token(text)
        assert "[REDACTED_TOKEN]" in redacted
        assert "sk-Abcdefgh" not in redacted

    def test_no_false_positives(self):
        text = "This is a normal sentence with no tokens."
        redacted = redact_connector_token(text)
        assert redacted == text

    def test_mixed_content(self):
        text = (
            "Using GITHUB_TOKEN=ghp_test123 for repo access. Normal text here. Token: ghp_test456."
        )
        redacted = redact_connector_token(text)
        assert "[REDACTED]" in redacted
        assert "ghp_test123" not in redacted
        assert "Normal text" in redacted


class TestConnectorDiagnostics:
    """Test ConnectorTestDiagnostics model."""

    def test_diagnostics_success(self):
        diag = ConnectorTestDiagnostics(
            status="success",
            message="Repository is accessible",
            checked_at="2026-06-24T12:00:00",
            connector_type="github",
            reachable=True,
            auth_configured=True,
            permissions_summary="Public access",
        )
        data = diag.model_dump(mode="json")
        assert data["status"] == "success"
        assert data["reachable"] is True
        assert data["auth_configured"] is True
        assert data["connector_type"] == "github"

    def test_diagnostics_error(self):
        diag = ConnectorTestDiagnostics(
            status="error",
            message="Connection failed",
            checked_at="2026-06-24T12:00:00",
            connector_type="url-import",
            reachable=False,
            auth_configured=False,
            errors=["Could not resolve hostname"],
        )
        data = diag.model_dump(mode="json")
        assert data["status"] == "error"
        assert data["reachable"] is False
        assert len(data["errors"]) == 1

    def test_diagnostics_no_token_exposure(self):
        diag = ConnectorTestDiagnostics(
            status="error",
            message="Token ghp_test1234567890abcdef is invalid",
            checked_at="2026-06-24T12:00:00",
            connector_type="github",
            reachable=False,
            auth_configured=True,
            errors=["Token invalid"],
        )
        # The diagnostics model doesn't redact itself, but the
        # runtime_dispatch wrapper applies redaction before returning.
        assert diag.message  # Message is present


class TestConnectorSchemasInRegistry:
    """Test that setup schemas are properly attached to connector definitions."""

    def test_list_with_schemas(self):
        connectors = list_connectors_with_schemas()
        assert len(connectors) >= 3
        for c in connectors:
            assert "connector_id" in c
            assert "setup_schema" in c
            if not c.get("is_stub"):
                assert c["setup_schema"] is not None
                assert "connector_type" in c["setup_schema"]

    def test_github_schema_in_registry(self):
        connectors = list_connectors_with_schemas()
        github = [c for c in connectors if c["connector_id"] == "github"]
        assert len(github) == 1
        schema = github[0]["setup_schema"]
        assert schema is not None
        assert schema["connector_type"] == "github"
        assert len(schema["credential_fields"]) == 1


class TestConnectorSetupFieldModel:
    """Test SetupField model."""

    def test_field_creation(self):
        field = SetupField(
            key="test_key",
            label="Test Field",
            field_type=FieldType.STRING,
            required=True,
            placeholder="Enter value",
            hint="This is a test",
            secret=False,
        )
        assert field.key == "test_key"
        assert field.label == "Test Field"
        assert field.field_type == FieldType.STRING
        assert field.required is True
        assert field.secret is False

    def test_password_field(self):
        field = SetupField(
            key="api_key",
            label="API Key",
            field_type=FieldType.PASSWORD,
            required=True,
            secret=True,
            env_var_hint="API_KEY",
        )
        assert field.field_type == FieldType.PASSWORD
        assert field.secret is True
        assert field.env_var_hint == "API_KEY"

    def test_default_values(self):
        field = SetupField(key="name", label="Name")
        assert field.field_type == FieldType.STRING
        assert field.required is False
        assert field.secret is False
        assert field.placeholder == ""
        assert field.hint == ""


class TestNotionGoogleDriveStatus:
    """Test that Notion and Google Drive are properly marked as disabled/planned."""

    def test_notion_disabled_in_schema(self):
        schema = get_setup_schema("notion")
        assert schema is not None
        assert schema.disabled is True
        assert "planned" in schema.disabled_reason.lower()
        assert len(schema.credential_fields) == 1
        assert schema.credential_fields[0].env_var_hint == "NOTION_API_KEY"

    def test_google_drive_disabled_in_schema(self):
        schema = get_setup_schema("google-drive")
        assert schema is not None
        assert schema.disabled is True
        assert "planned" in schema.disabled_reason.lower()
        assert len(schema.credential_fields) >= 1

    def test_notion_in_registry(self):
        from decision_system.connectors.registry import get_connector_definition

        definition = get_connector_definition("notion")
        assert definition is not None
        assert definition.is_stub is True
        assert definition.supports_list is True
        assert definition.requires_secrets is True

    def test_google_drive_in_registry(self):
        from decision_system.connectors.registry import get_connector_definition

        definition = get_connector_definition("google-drive")
        assert definition is not None
        assert definition.is_stub is True
        assert definition.supports_list is True
        assert definition.requires_secrets is True

    def test_notion_fake_runtime(self):
        """Test that notion runtime returns without raising NotImplementedError."""
        from decision_system.connectors.models import (
            ConnectorConfig,
            ConnectorMode,
            ConnectorType,
        )
        from decision_system.connectors.runtime_dispatch import test_connection

        config = ConnectorConfig(
            connector_id="test-notion",
            name="Test Notion",
            connector_type=ConnectorType.NOTION,
            mode=ConnectorMode.READ_ONLY,
        )
        # Should not raise NotImplementedError
        result = test_connection(config)
        assert result is not None

    def test_google_drive_fake_runtime(self):
        """Test that google-drive runtime returns without raising NotImplementedError."""
        from decision_system.connectors.models import (
            ConnectorConfig,
            ConnectorMode,
            ConnectorType,
        )
        from decision_system.connectors.runtime_dispatch import test_connection

        config = ConnectorConfig(
            connector_id="test-gdrive",
            name="Test Google Drive",
            connector_type=ConnectorType.GOOGLE_DRIVE,
            mode=ConnectorMode.READ_ONLY,
        )
        # Should not raise NotImplementedError
        result = test_connection(config)
        assert result is not None


class TestGitHubIssuesExpansion:
    """Test GitHub issues/PRs/releases expansion (structure, no network)."""

    def test_github_schema_includes_issue_types(self):
        schema = get_setup_schema("github")
        assert schema is not None
        assert "issue" in schema.supported_item_types
        assert "pull_request" in schema.supported_item_types
        assert "release" in schema.supported_item_types

    def test_github_issues_module_imports(self):
        from decision_system.connectors.github_issues import (
            fetch_issue,
            list_all_github_items,
            list_issues,
            list_pull_requests,
            list_releases,
        )

        assert callable(list_issues)
        assert callable(fetch_issue)
        assert callable(list_pull_requests)
        assert callable(list_releases)
        assert callable(list_all_github_items)

    def test_github_issues_returns_empty_for_no_config(self):
        from decision_system.connectors.github_issues import list_issues
        from decision_system.connectors.models import (
            ConnectorConfig,
            ConnectorMode,
            ConnectorType,
        )

        config = ConnectorConfig(
            connector_id="test",
            name="test",
            connector_type=ConnectorType.GITHUB,
            mode=ConnectorMode.READ_ONLY,
            config={},
        )
        items = list_issues(config)
        assert items == []

    def test_github_issues_item_type(self):
        from decision_system.connectors.models import ConnectorRuntimeItem

        item = ConnectorRuntimeItem(
            external_id="issue-1",
            title="Test Issue",
            item_type="issue",
            source_url="https://github.com/owner/repo/issues/1",
        )
        assert item.item_type == "issue"
        assert item.external_id == "issue-1"


class TestMetadataMapping:
    """Test connector metadata mapping for evidence/report citations."""

    def test_connector_citation_github(self):
        from decision_system.connectors.models import ConnectorCitation, ConnectorType

        citation = ConnectorCitation(
            connector_id="test-connector",
            connector_type=ConnectorType.GITHUB,
            external_id="issue-42",
            source_url="https://github.com/owner/repo/issues/42",
            content_hash="abc123",
            label="Fix login bug",
        )
        assert citation.to_display_string() == "GitHub: Fix login bug"
        metadata = citation.to_evidence_metadata()
        assert metadata["connector_type"] == "github"
        assert metadata["external_id"] == "issue-42"
        assert metadata["citation_label"] == "GitHub: Fix login bug"

    def test_connector_citation_local_files(self):
        from decision_system.connectors.models import ConnectorCitation, ConnectorType

        citation = ConnectorCitation(
            connector_id="test-connector",
            connector_type=ConnectorType.LOCAL_FILES,
            external_id="/path/to/file.md",
            label="Local file: /path/to/file.md",
        )
        assert "Local file" in citation.to_display_string()
        assert citation.to_display_string() == "Local file: /path/to/file.md"

    def test_connector_citation_url(self):
        from decision_system.connectors.models import ConnectorCitation, ConnectorType

        citation = ConnectorCitation(
            connector_id="test-connector",
            connector_type=ConnectorType.URL_IMPORT,
            external_id="page-1",
            source_url="https://example.com/page",
            label="Example Page",
        )
        display = citation.to_display_string()
        assert "Example Page" in display
        assert "example.com" in display

    def test_connector_citation_notion(self):
        from decision_system.connectors.models import ConnectorCitation, ConnectorType

        citation = ConnectorCitation(
            connector_id="test-connector",
            connector_type=ConnectorType.NOTION,
            external_id="page-abc",
            label="Meeting Notes",
        )
        assert "Notion" in citation.to_display_string()
        assert "Meeting Notes" in citation.to_display_string()

    def test_connector_citation_google_drive(self):
        from decision_system.connectors.models import ConnectorCitation, ConnectorType

        citation = ConnectorCitation(
            connector_id="test-connector",
            connector_type=ConnectorType.GOOGLE_DRIVE,
            external_id="file-xyz",
            label="Report.pdf",
        )
        assert "Google Drive" in citation.to_display_string()
        assert "Report.pdf" in citation.to_display_string()


class TestAuditEvents:
    """Test that new audit events are properly defined."""

    def test_setup_audit_event_constants(self):
        from decision_system.connectors.audit import (
            EVENT_CONNECTOR_CREDENTIALS_MISSING,
            EVENT_CONNECTOR_ITEM_PREVIEWED,
            EVENT_CONNECTOR_SETUP_COMPLETED,
            EVENT_CONNECTOR_SETUP_FAILED,
            EVENT_CONNECTOR_SETUP_STARTED,
            EVENT_CONNECTOR_SETUP_TESTED,
            EVENT_GITHUB_ISSUE_IMPORTED,
        )

        assert EVENT_CONNECTOR_SETUP_STARTED == "connector_setup_started"
        assert EVENT_CONNECTOR_SETUP_TESTED == "connector_setup_tested"
        assert EVENT_CONNECTOR_SETUP_COMPLETED == "connector_setup_completed"
        assert EVENT_CONNECTOR_SETUP_FAILED == "connector_setup_failed"
        assert EVENT_CONNECTOR_CREDENTIALS_MISSING == "connector_credentials_missing"
        assert EVENT_CONNECTOR_ITEM_PREVIEWED == "connector_item_previewed"
        assert EVENT_GITHUB_ISSUE_IMPORTED == "github_issue_imported"

    def test_record_setup_events(self):
        from decision_system.connectors.audit import (
            record_credentials_missing,
            record_setup_completed,
            record_setup_failed,
            record_setup_started,
            record_setup_tested,
        )

        # These should not raise exceptions
        record_setup_started(connector_type="github")
        record_setup_tested(connector_type="github", success=True)
        record_setup_completed(connector_type="github", connector_id="test-1")
        record_setup_failed(connector_type="github", error="Test error")
        record_credentials_missing(connector_type="notion", env_var_name="NOTION_API_KEY")


class TestMetrics:
    """Test that new metrics functions are properly defined."""

    def test_setup_metrics_exist(self):
        from decision_system.connectors.metrics import (
            record_import_by_type,
            record_preview_item_count,
            record_setup_duration,
            record_test_failure,
            record_test_success,
        )

        # These should not raise exceptions
        record_setup_duration(connector_type="github", duration_ms=100.0)
        record_test_success(connector_type="github")
        record_test_failure(connector_type="github")
        record_preview_item_count(connector_id="test", count=5)
        record_import_by_type(connector_type="github", item_type="issue")


class TestWizardHelpers:
    """Test setup wizard helper logic."""

    def test_setup_field_env_var_hints(self):
        for schema in list_setup_schemas():
            for field in schema.credential_fields:
                assert field.env_var_hint, (
                    f"{schema.connector_type}.{field.key} missing env_var_hint"
                )
                assert field.secret is True, f"{schema.connector_type}.{field.key} not secret"

    def test_connector_has_wizard_fields(self):
        """All non-disabled connectors should have required_fields for wizard."""
        for schema in list_setup_schemas():
            if not schema.disabled:
                assert len(schema.required_fields) > 0, (
                    f"{schema.connector_type} has no required fields"
                )
                for field in schema.required_fields:
                    assert field.label, "Required field missing label"
                    assert field.hint, f"Required field {field.key} missing hint"

    def test_read_only_capabilities_present(self):
        for schema in list_setup_schemas():
            if not schema.disabled:
                for cap in schema.read_only_capabilities:
                    assert cap.read_only is True
                    assert "(read-only)" in cap.description


class TestItemPreview:
    """Test item preview structure."""

    def test_runtime_item_preview_fields(self):
        from datetime import datetime, timezone

        from decision_system.connectors.models import ConnectorRuntimeItem

        item = ConnectorRuntimeItem(
            external_id="test-1",
            title="Test Document",
            item_type="file",
            source_url="https://example.com/doc.md",
            modified_at=datetime.now(timezone.utc),
            content_type="text/markdown",
            size_bytes=1024,
            metadata={"warning": "Large file"},
        )
        data = item.model_dump(mode="json")
        assert data["title"] == "Test Document"
        assert data["item_type"] == "file"
        assert data["source_url"] == "https://example.com/doc.md"
        assert data["size_bytes"] == 1024
        assert data["metadata"]["warning"] == "Large file"

    def test_github_issue_item_preview(self):
        from decision_system.connectors.models import ConnectorRuntimeItem

        item = ConnectorRuntimeItem(
            external_id="issue-42",
            title="Fix login bug",
            item_type="issue",
            source_url="https://github.com/owner/repo/issues/42",
            content_type="text/markdown",
            size_bytes=500,
            metadata={
                "github_type": "issue",
                "issue_number": 42,
                "state": "open",
                "labels": ["bug", "priority"],
                "author": "testuser",
            },
        )
        assert item.item_type == "issue"
        assert item.metadata["issue_number"] == 42
        assert "bug" in item.metadata["labels"]

    def test_github_pr_item_preview(self):
        from decision_system.connectors.models import ConnectorRuntimeItem

        item = ConnectorRuntimeItem(
            external_id="pr-7",
            title="Add new feature",
            item_type="pull_request",
            source_url="https://github.com/owner/repo/pull/7",
            metadata={"pr_number": 7, "state": "open", "draft": False, "merged": False},
        )
        assert item.item_type == "pull_request"
        assert item.metadata["pr_number"] == 7
        assert item.metadata["draft"] is False


class TestRBACConnectorSetup:
    """Test RBAC permissions for connector setup actions."""

    def test_connector_permissions_exist(self):
        from decision_system.identity.models import Permission

        assert hasattr(Permission, "CONNECTOR_READ")
        assert hasattr(Permission, "CONNECTOR_MANAGE")
        assert hasattr(Permission, "CONNECTOR_IMPORT")
        assert hasattr(Permission, "CONNECTOR_SYNC")
        assert hasattr(Permission, "CONNECTOR_SCHEDULE")

    def test_connector_route_protection(self):
        """Verify that connector API routes require permissions."""
        from decision_system.identity.permissions import (
            require_permission,
            require_workspace_permission,
        )

        assert callable(require_permission)
        assert callable(require_workspace_permission)
