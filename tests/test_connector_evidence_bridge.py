"""Tests for the connector-to-evidence bridge (evidence_bridge.py).

Validates the full pipeline: ConnectorFetchedContent -> DataSource records
-> text chunks -> Chroma indexing, with dedup and update semantics.
"""

from __future__ import annotations

import os
import shutil
import tempfile

import pytest

from decision_system.connectors.evidence_bridge import persist_connector_content
from decision_system.connectors.models import ConnectorFetchedContent
from decision_system.data_sources.store import DataSourceStore


@pytest.fixture
def temp_data_dir():
    """Provide a temporary data directory and clean up afterward."""
    tmp = tempfile.mkdtemp(prefix="ds_test_evb_")
    old_val = os.environ.get("DECISION_SYSTEM_DATA_DIR", "")
    os.environ["DECISION_SYSTEM_DATA_DIR"] = tmp
    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)
    if old_val:
        os.environ["DECISION_SYSTEM_DATA_DIR"] = old_val
    else:
        os.environ.pop("DECISION_SYSTEM_DATA_DIR", None)


@pytest.fixture
def sample_content() -> list[ConnectorFetchedContent]:
    """Sample connector content for testing."""
    return [
        ConnectorFetchedContent(
            external_id="url:https://example.com/report",
            title="Example Report",
            filename="report.html",
            content_text="This is a test report about company finances. Revenue grew 20%.",
            content_type="text/html",
            metadata={"url": "https://example.com/report", "content_type": "text/html"},
        ),
        ConnectorFetchedContent(
            external_id="url:https://example.com/analysis",
            title="Market Analysis",
            filename="analysis.txt",
            content_text="Market trends show growth in the enterprise sector.",
            content_type="text/plain",
            metadata={"url": "https://example.com/analysis", "content_type": "text/plain"},
        ),
    ]


class TestEvidenceBridge:
    """Test suite for the connector-to-evidence bridge."""

    def test_persist_creates_datasources(self, temp_data_dir, sample_content):
        """Connector content creates DataSource records."""
        result = persist_connector_content(
            workspace_id="ws_test",
            content_list=sample_content,
            connector_name="Test Connector",
            connector_id="test-connector-1",
        )
        assert result["data_sources_created"] == 2
        assert result["chunks_parsed"] > 0
        assert len(result["errors"]) == 0

        store = DataSourceStore()
        sources = store.list_by_workspace("ws_test")
        assert len(sources) >= 2

    def test_indexes_into_chroma(self, temp_data_dir, sample_content):
        """Chunks are indexed into the Chroma vector store."""
        result = persist_connector_content(
            workspace_id="ws_test",
            content_list=sample_content,
            connector_name="Test Connector",
            connector_id="test-connector-1",
        )
        assert result["chunks_indexed"] > 0

    def test_preserves_connector_metadata(self, temp_data_dir, sample_content):
        """DataSource metadata preserves connector_id and external_id."""
        persist_connector_content(
            workspace_id="ws_test",
            content_list=sample_content,
            connector_name="Test Connector",
            connector_id="test-connector-1",
        )
        store = DataSourceStore()
        sources = store.list_by_workspace("ws_test")
        src = sources[0]
        assert src.metadata is not None
        assert src.metadata.get("connector_id") == "test-connector-1"
        assert src.metadata.get("external_id") == sample_content[0].external_id
        assert src.status == "parsed"

    def test_dedup_unchanged_content(self, temp_data_dir, sample_content):
        """Re-importing unchanged content does not create duplicate DataSources."""
        persist_connector_content(
            workspace_id="ws_test",
            content_list=sample_content,
            connector_name="Test Connector",
            connector_id="test-connector-1",
        )
        store = DataSourceStore()
        count_before = len(store.list_by_workspace("ws_test"))

        persist_connector_content(
            workspace_id="ws_test",
            content_list=sample_content,
            connector_name="Test Connector",
            connector_id="test-connector-1",
        )
        count_after = len(store.list_by_workspace("ws_test"))
        assert count_after == count_before

    def test_update_changed_content(self, temp_data_dir, sample_content):
        """Updating content reuses existing DataSource record (no duplicate)."""
        persist_connector_content(
            workspace_id="ws_test",
            content_list=sample_content,
            connector_name="Test Connector",
            connector_id="test-connector-1",
        )
        store = DataSourceStore()
        count_before = len(store.list_by_workspace("ws_test"))

        changed = [
            ConnectorFetchedContent(
                external_id="url:https://example.com/report",
                title="Updated Report",
                filename="report.html",
                content_text="UPDATED content with new information.",
                content_type="text/html",
                metadata={"url": "https://example.com/report", "content_type": "text/html"},
            ),
        ]
        persist_connector_content(
            workspace_id="ws_test",
            content_list=changed,
            connector_name="Test Connector",
            connector_id="test-connector-1",
        )
        count_after = len(store.list_by_workspace("ws_test"))
        assert count_after == count_before

    def test_empty_content_skipped(self, temp_data_dir):
        """Content items with no text or bytes are skipped gracefully."""
        empty = [
            ConnectorFetchedContent(
                external_id="url:https://example.com/empty",
                title="Empty",
                filename="empty.txt",
                content_text="",
                content_type="text/plain",
                metadata={},
            ),
        ]
        result = persist_connector_content(
            workspace_id="ws_test",
            content_list=empty,
            connector_name="Test Connector",
            connector_id="test-connector-1",
        )
        assert result["data_sources_created"] == 0
        assert result["chunks_parsed"] == 0
