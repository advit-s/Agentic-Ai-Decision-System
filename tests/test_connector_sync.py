"""Tests for v1.29 connector sync — state model, schedule, runner, and API."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from decision_system.connectors.import_jobs import run_sync
from decision_system.connectors.models import (
    ConnectorType,
)
from decision_system.connectors.schedule import (
    ConnectorSchedule,
    ScheduleStore,
    reset_schedule_store,
)
from decision_system.connectors.sync_runner import (
    SyncRunner,
    reset_sync_runner,
)
from decision_system.connectors.sync_state import (
    SyncStateItem,
    SyncStateStore,
    reset_sync_state_store,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clean_stores():
    """Reset singleton stores before each test."""
    reset_sync_state_store()
    reset_schedule_store()
    reset_sync_runner()
    yield


@pytest.fixture
def sync_state_store(tmp_path: Path) -> SyncStateStore:
    return SyncStateStore(base_dir=tmp_path / "sync_state")


@pytest.fixture
def schedule_store(tmp_path: Path) -> ScheduleStore:
    return ScheduleStore(base_dir=tmp_path / "schedules")


# ---------------------------------------------------------------------------
# SyncStateItem model
# ---------------------------------------------------------------------------


class TestSyncStateItem:
    def test_minimal(self):
        item = SyncStateItem(connector_id="test-conn", external_id="doc1")
        assert item.sync_state_id
        assert item.connector_id == "test-conn"
        assert item.external_id == "doc1"
        assert item.status == "new"
        assert item.last_seen_at

    def test_new_status_default(self):
        item = SyncStateItem(connector_id="c1", external_id="e1")
        assert item.status == "new"

    def test_json_serialization(self):
        item = SyncStateItem(
            connector_id="c1",
            external_id="e1",
            content_hash="abc123",
            status="unchanged",
        )
        data = item.model_dump(mode="json")
        assert data["connector_id"] == "c1"
        assert data["external_id"] == "e1"
        assert data["content_hash"] == "abc123"
        assert data["status"] == "unchanged"


# ---------------------------------------------------------------------------
# SyncStateStore
# ---------------------------------------------------------------------------


class TestSyncStateStore:
    def test_empty_store(self, sync_state_store: SyncStateStore):
        state = sync_state_store.get_sync_state("ws1", "c1")
        assert state == []

    def test_upsert_new_item(self, sync_state_store: SyncStateStore):
        item = SyncStateItem(workspace_id="ws1", connector_id="c1", external_id="e1")
        sync_state_store.upsert_item("ws1", item)
        state = sync_state_store.get_sync_state("ws1", "c1")
        assert len(state) == 1
        assert state[0].external_id == "e1"
        assert state[0].status == "new"

    def test_upsert_update_item(self, sync_state_store: SyncStateStore):
        item = SyncStateItem(workspace_id="ws1", connector_id="c1", external_id="e1")
        sync_state_store.upsert_item("ws1", item)
        item.status = "changed"
        sync_state_store.upsert_item("ws1", item)
        state = sync_state_store.get_sync_state("ws1", "c1")
        assert len(state) == 1
        assert state[0].status == "changed"

    def test_get_item(self, sync_state_store: SyncStateStore):
        item = SyncStateItem(workspace_id="ws1", connector_id="c1", external_id="e1")
        sync_state_store.upsert_item("ws1", item)
        found = sync_state_store.get_item("ws1", "c1", "e1")
        assert found is not None
        assert found.external_id == "e1"
        not_found = sync_state_store.get_item("ws1", "c1", "nonexistent")
        assert not_found is None

    def test_mark_seen_new(self, sync_state_store: SyncStateStore):
        item = sync_state_store.mark_seen("ws1", "c1", "e1", content_hash="abc", status="new")
        assert item.status == "new"
        assert item.content_hash == "abc"
        state = sync_state_store.get_sync_state("ws1", "c1")
        assert len(state) == 1

    def test_mark_seen_existing(self, sync_state_store: SyncStateStore):
        sync_state_store.mark_seen("ws1", "c1", "e1", content_hash="abc", status="new")
        sync_state_store.mark_seen("ws1", "c1", "e1", content_hash="def", status="changed")
        state = sync_state_store.get_sync_state("ws1", "c1")
        assert len(state) == 1
        assert state[0].content_hash == "def"
        assert state[0].status == "changed"

    def test_mark_deleted_remote(self, sync_state_store: SyncStateStore):
        sync_state_store.mark_seen("ws1", "c1", "e1")
        item = sync_state_store.mark_deleted_remote("ws1", "c1", "e1")
        assert item is not None
        assert item.status == "deleted_remote"

    def test_mark_deleted_remote_nonexistent(self, sync_state_store: SyncStateStore):
        item = sync_state_store.mark_deleted_remote("ws1", "c1", "nonexistent")
        assert item is None

    def test_mark_imported(self, sync_state_store: SyncStateStore):
        sync_state_store.mark_seen("ws1", "c1", "e1")
        item = sync_state_store.mark_imported("ws1", "c1", "e1", local_source_id="src1")
        assert item is not None
        assert item.status == "unchanged"
        assert item.local_source_id == "src1"
        assert item.last_imported_at is not None

    def test_delete_connector_state(self, sync_state_store: SyncStateStore):
        sync_state_store.mark_seen("ws1", "c1", "e1")
        sync_state_store.delete_connector_state("ws1", "c1")
        state = sync_state_store.get_sync_state("ws1", "c1")
        assert state == []

    def test_compute_hash(self, sync_state_store: SyncStateStore):
        h1 = sync_state_store.compute_hash("hello")
        h2 = sync_state_store.compute_hash("hello")
        h3 = sync_state_store.compute_hash("world")
        assert h1 == h2
        assert h1 != h3
        assert len(h1) == 64  # SHA-256 hex length

    def test_workspace_isolation(self, sync_state_store: SyncStateStore):
        sync_state_store.mark_seen("ws1", "c1", "e1")
        sync_state_store.mark_seen("ws2", "c1", "e2")
        ws1_state = sync_state_store.get_sync_state("ws1", "c1")
        ws2_state = sync_state_store.get_sync_state("ws2", "c1")
        assert len(ws1_state) == 1
        assert len(ws2_state) == 1
        assert ws1_state[0].external_id == "e1"
        assert ws2_state[0].external_id == "e2"


# ---------------------------------------------------------------------------
# ConnectorSchedule model
# ---------------------------------------------------------------------------


class TestConnectorSchedule:
    def test_minimal(self):
        s = ConnectorSchedule(connector_id="c1")
        assert s.schedule_id
        assert s.connector_id == "c1"
        assert s.enabled is True
        assert s.schedule_type == "manual"

    def test_is_due_manual(self):
        s = ConnectorSchedule(connector_id="c1", schedule_type="manual")
        assert not s.is_due()

    def test_is_due_interval_not_due(self):
        s = ConnectorSchedule(
            connector_id="c1",
            schedule_type="interval",
            interval_minutes=60,
            created_at=datetime.now(timezone.utc),
        )
        s.next_run_at = s.calculate_next_run()
        # Just created — not due yet
        assert not s.is_due()

    def test_is_due_interval_due(self):
        s = ConnectorSchedule(
            connector_id="c1",
            schedule_type="interval",
            interval_minutes=60,
            last_run_at=datetime.now(timezone.utc) - timedelta(hours=2),
        )
        s.next_run_at = s.calculate_next_run()
        assert s.next_run_at is not None
        assert s.next_run_at < datetime.now(timezone.utc)
        assert s.is_due()

    def test_disabled_not_due(self):
        s = ConnectorSchedule(
            connector_id="c1",
            enabled=False,
            schedule_type="interval",
            interval_minutes=60,
        )
        assert not s.is_due()

    def test_calculate_next_run_manual(self):
        s = ConnectorSchedule(connector_id="c1", schedule_type="manual")
        assert s.calculate_next_run() is None

    def test_calculate_next_run_interval(self):
        s = ConnectorSchedule(
            connector_id="c1",
            schedule_type="interval",
            interval_minutes=30,
        )
        next_run = s.calculate_next_run()
        assert next_run is not None
        # Should be ~30 min from creation
        assert next_run > s.created_at

    def test_json_serialization(self):
        s = ConnectorSchedule(
            connector_id="c1",
            schedule_type="interval",
            interval_minutes=60,
            enabled=True,
        )
        data = s.model_dump(mode="json")
        assert data["connector_id"] == "c1"
        assert data["schedule_type"] == "interval"
        assert data["interval_minutes"] == 60
        assert data["enabled"] is True


# ---------------------------------------------------------------------------
# ScheduleStore
# ---------------------------------------------------------------------------


class TestScheduleStore:
    def test_empty(self, schedule_store: ScheduleStore):
        schedules = schedule_store.list_schedules("ws1", "c1")
        assert schedules == []

    def test_create_and_list(self, schedule_store: ScheduleStore):
        s = ConnectorSchedule(workspace_id="ws1", connector_id="c1")
        schedule_store.create_schedule("ws1", s)
        schedules = schedule_store.list_schedules("ws1", "c1")
        assert len(schedules) == 1
        assert schedules[0].schedule_id == s.schedule_id

    def test_get_schedule(self, schedule_store: ScheduleStore):
        s = ConnectorSchedule(workspace_id="ws1", connector_id="c1")
        schedule_store.create_schedule("ws1", s)
        found = schedule_store.get_schedule("ws1", "c1", s.schedule_id)
        assert found is not None
        assert found.schedule_id == s.schedule_id
        not_found = schedule_store.get_schedule("ws1", "c1", "nonexistent")
        assert not_found is None

    def test_update_schedule(self, schedule_store: ScheduleStore):
        s = ConnectorSchedule(workspace_id="ws1", connector_id="c1", enabled=True)
        schedule_store.create_schedule("ws1", s)
        s.enabled = False
        updated = schedule_store.update_schedule("ws1", s)
        assert updated is not None
        assert not updated.enabled

    def test_update_nonexistent(self, schedule_store: ScheduleStore):
        s = ConnectorSchedule(workspace_id="ws1", connector_id="c1")
        result = schedule_store.update_schedule("ws1", s)
        assert result is None

    def test_delete_schedule(self, schedule_store: ScheduleStore):
        s = ConnectorSchedule(workspace_id="ws1", connector_id="c1")
        schedule_store.create_schedule("ws1", s)
        deleted = schedule_store.delete_schedule("ws1", "c1", s.schedule_id)
        assert deleted
        schedules = schedule_store.list_schedules("ws1", "c1")
        assert len(schedules) == 0

    def test_delete_nonexistent(self, schedule_store: ScheduleStore):
        deleted = schedule_store.delete_schedule("ws1", "c1", "nonexistent")
        assert not deleted

    def test_toggle_schedule(self, schedule_store: ScheduleStore):
        s = ConnectorSchedule(workspace_id="ws1", connector_id="c1", enabled=True)
        schedule_store.create_schedule("ws1", s)
        toggled = schedule_store.toggle_schedule("ws1", "c1", s.schedule_id)
        assert toggled is not None
        assert not toggled.enabled
        # Toggle again
        toggled = schedule_store.toggle_schedule("ws1", "c1", s.schedule_id)
        assert toggled.enabled

    def test_list_due_schedules(self, schedule_store: ScheduleStore):
        # Create a past-due interval schedule
        past = datetime.now(timezone.utc) - timedelta(hours=2)
        s = ConnectorSchedule(
            workspace_id="ws1",
            connector_id="c1",
            schedule_type="interval",
            interval_minutes=60,
            last_run_at=past,
        )
        s.next_run_at = s.calculate_next_run()
        schedule_store.create_schedule("ws1", s)

        # Create a non-due manual schedule
        s2 = ConnectorSchedule(
            workspace_id="ws1",
            connector_id="c2",
            schedule_type="manual",
        )
        schedule_store.create_schedule("ws1", s2)

        due = schedule_store.list_due_schedules()
        assert len(due) == 1
        assert due[0].connector_id == "c1"

    def test_workspace_isolation(self, schedule_store: ScheduleStore):
        s1 = ConnectorSchedule(workspace_id="ws1", connector_id="c1")
        schedule_store.create_schedule("ws1", s1)
        s2 = ConnectorSchedule(workspace_id="ws2", connector_id="c1")
        schedule_store.create_schedule("ws2", s2)
        assert len(schedule_store.list_schedules("ws1", "c1")) == 1
        assert len(schedule_store.list_schedules("ws2", "c1")) == 1


# ---------------------------------------------------------------------------
# SyncRunner (unit tests)
# ---------------------------------------------------------------------------


class TestSyncRunner:
    def test_sync_connector_no_config_returns_error(self):
        runner = SyncRunner()
        result = runner.sync_connector("nonexistent", "ws1")
        assert result.status == "failed"
        assert "not found" in (result.error or "").lower()

    def test_run_due_schedules_empty(self):
        runner = SyncRunner()
        results = runner.run_due_schedules()
        assert results == []


# ---------------------------------------------------------------------------
# run_sync helper
# ---------------------------------------------------------------------------


class TestRunSync:
    def test_run_sync_nonexistent(self):
        result = run_sync("nonexistent", "ws1")
        assert result["status"] == "failed"

    # ---------------------------------------------------------------------------
    # Sync API tests
    # ---------------------------------------------------------------------------

    def test_connector_citation_display(self):
        from decision_system.connectors.models import ConnectorCitation

        citation = ConnectorCitation(
            connector_id="c1",
            connector_type=ConnectorType.LOCAL_FILES,
            external_id="doc1",
            label="My Document",
            content_hash="abc123",
        )
        display = citation.to_display_string()
        assert "My Document" in display
        assert "My Document" in display

        meta = citation.to_evidence_metadata()
        assert meta["connector_id"] == "c1"
        assert meta["connector_type"] == "local-files"


# ---------------------------------------------------------------------------
# Integration: sync state transitions
# ---------------------------------------------------------------------------


class TestSyncStateTransitions:
    def test_new_item_imported(self, sync_state_store: SyncStateStore):
        """New item → import → becomes unchanged."""
        item = sync_state_store.mark_seen("ws1", "c1", "e1", content_hash="abc", status="new")
        assert item.status == "new"
        item = sync_state_store.mark_imported("ws1", "c1", "e1")
        assert item.status == "unchanged"

    def test_changed_item_reimported(self, sync_state_store: SyncStateStore):
        """Changed item → mark_seen with new hash → mark_imported."""
        sync_state_store.mark_seen("ws1", "c1", "e1", content_hash="abc")
        sync_state_store.mark_imported("ws1", "c1", "e1")
        item = sync_state_store.mark_seen("ws1", "c1", "e1", content_hash="def", status="changed")
        assert item.status == "changed"
        item = sync_state_store.mark_imported("ws1", "c1", "e1")
        assert item.status == "unchanged"

    def test_deleted_remote_preserved(self, sync_state_store: SyncStateStore):
        """Deleted remote items are marked but not removed from store."""
        sync_state_store.mark_seen("ws1", "c1", "e1")
        item = sync_state_store.mark_deleted_remote("ws1", "c1", "e1")
        assert item.status == "deleted_remote"
        # Item still in store
        state = sync_state_store.get_sync_state("ws1", "c1")
        assert len(state) == 1
        assert state[0].status == "deleted_remote"
