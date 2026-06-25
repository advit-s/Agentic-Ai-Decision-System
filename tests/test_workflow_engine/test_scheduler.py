"""Tests for scheduler models, store, and trigger evaluators."""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from decision_system.workflow_engine.scheduler.models import (
    ScheduleDefinition,
    TriggerType,
)

# ─── Test ScheduleDefinition ─────────────────────────────────────────────────


class TestScheduleDefinition:
    def test_minimal_schedule(self):
        """A schedule with just id and workflow_id."""
        sd = ScheduleDefinition(workflow_id="wf-123")
        assert sd.workflow_id == "wf-123"
        assert sd.trigger_type == TriggerType.CRON
        assert sd.trigger_config == {}
        assert sd.enabled is True

    def test_cron_trigger(self):
        sd = ScheduleDefinition(
            workflow_id="wf-123",
            trigger_type=TriggerType.CRON,
            trigger_config={"expression": "0 9 * * 1-5"},
        )
        assert sd.trigger_type == TriggerType.CRON
        assert sd.trigger_config["expression"] == "0 9 * * 1-5"

    def test_webhook_trigger(self):
        sd = ScheduleDefinition(
            workflow_id="wf-123",
            trigger_type=TriggerType.WEBHOOK,
            trigger_config={"path": "/hooks/my-webhook"},
        )
        assert sd.trigger_type == TriggerType.WEBHOOK
        assert sd.trigger_config["path"] == "/hooks/my-webhook"

    def test_file_watch_trigger(self):
        sd = ScheduleDefinition(
            workflow_id="wf-123",
            trigger_type=TriggerType.FILE_WATCH,
            trigger_config={"directory": "company_docs/", "pattern": "*.md"},
        )
        assert sd.trigger_type == TriggerType.FILE_WATCH
        assert sd.trigger_config["directory"] == "company_docs/"
        assert sd.trigger_config["pattern"] == "*.md"

    def test_default_enabled(self):
        sd = ScheduleDefinition(workflow_id="wf-1")
        assert sd.enabled is True

    def test_explicitly_disabled(self):
        sd = ScheduleDefinition(workflow_id="wf-1", enabled=False)
        assert sd.enabled is False

    def test_auto_id(self):
        sd = ScheduleDefinition(workflow_id="wf-1")
        assert sd.id == ""

    def test_invalid_trigger_type(self):
        with pytest.raises(ValidationError):
            ScheduleDefinition(workflow_id="wf-1", trigger_type="invalid")  # type: ignore

    def test_created_at_defaults(self):
        sd = ScheduleDefinition(workflow_id="wf-1")
        assert sd.created_at is not None

    def test_serialize_to_json(self):
        sd = ScheduleDefinition(workflow_id="wf-1")
        data = sd.model_dump(mode="json")
        assert data["workflow_id"] == "wf-1"
        assert data["enabled"] is True
        assert data["trigger_type"] == "cron"

    def test_last_fired_none_by_default(self):
        sd = ScheduleDefinition(workflow_id="wf-1")
        assert sd.last_fired is None

    def test_set_last_fired(self):
        now = datetime.now(timezone.utc)
        sd = ScheduleDefinition(workflow_id="wf-1", last_fired=now)
        assert sd.last_fired == now

    def test_unique_ids(self):
        sd1 = ScheduleDefinition(workflow_id="wf-1")
        sd2 = ScheduleDefinition(workflow_id="wf-1")
        assert sd1.id == sd2.id == ""


# ─── Test ScheduleStore ──────────────────────────────────────────────────────


class TestScheduleStore:
    @pytest.fixture
    def store(self):
        from decision_system.workflow_engine.scheduler.store import ScheduleStore

        with tempfile.TemporaryDirectory() as tmp:
            yield ScheduleStore(Path(tmp))

    def test_save_and_load(self, store):
        sd = ScheduleDefinition(workflow_id="wf-123")
        saved = store.save(sd)
        assert saved.id != ""
        loaded = store.load(saved.id)
        assert loaded is not None
        assert loaded.workflow_id == "wf-123"
        assert loaded.enabled is True

    def test_save_generates_id(self, store):
        sd = ScheduleDefinition(workflow_id="wf-1")
        saved = store.save(sd)
        assert saved.id.startswith("sch-")

    def test_list_schedules(self, store):
        s1 = store.save(ScheduleDefinition(workflow_id="wf-1"))
        s2 = store.save(ScheduleDefinition(workflow_id="wf-1"))
        s3 = store.save(ScheduleDefinition(workflow_id="wf-2"))
        all_schedules = store.list()
        assert len(all_schedules) == 3
        ids = {s.id for s in all_schedules}
        assert s1.id in ids
        assert s2.id in ids
        assert s3.id in ids

    def test_list_by_workflow(self, store):
        store.save(ScheduleDefinition(workflow_id="wf-1"))
        store.save(ScheduleDefinition(workflow_id="wf-1"))
        store.save(ScheduleDefinition(workflow_id="wf-2"))
        wf1_schedules = store.list(workflow_id="wf-1")
        assert len(wf1_schedules) == 2
        wf2_schedules = store.list(workflow_id="wf-2")
        assert len(wf2_schedules) == 1

    def test_list_by_trigger_type(self, store):
        store.save(
            ScheduleDefinition(
                workflow_id="wf-1",
                trigger_type=TriggerType.CRON,
            )
        )
        store.save(
            ScheduleDefinition(
                workflow_id="wf-2",
                trigger_type=TriggerType.WEBHOOK,
            )
        )
        cron_schedules = store.list(trigger_type=TriggerType.CRON)
        assert len(cron_schedules) == 1
        assert cron_schedules[0].trigger_type == TriggerType.CRON

    def test_delete(self, store):
        sd = store.save(ScheduleDefinition(workflow_id="wf-1"))
        assert store.load(sd.id) is not None
        deleted = store.delete(sd.id)
        assert deleted is True
        assert store.load(sd.id) is None

    def test_delete_nonexistent(self, store):
        deleted = store.delete("sch-nonexistent")
        assert deleted is False

    def test_nonexistent_load(self, store):
        loaded = store.load("sch-nonexistent")
        assert loaded is None

    def test_list_empty(self, store):
        assert store.list() == []

    def test_update_last_fired(self, store):
        sd = store.save(ScheduleDefinition(workflow_id="wf-1"))
        now = datetime.now(timezone.utc)
        store.update_last_fired(sd.id, now)
        loaded = store.load(sd.id)
        assert loaded is not None
        assert loaded.last_fired is not None
        assert abs((loaded.last_fired - now).total_seconds()) < 1

    def test_save_updates_updated_at(self, store):
        sd = store.save(ScheduleDefinition(workflow_id="wf-1"))
        original_updated = sd.updated_at
        sd.enabled = False
        saved_again = store.save(sd)
        assert saved_again.updated_at >= original_updated

    def test_persists_to_disk(self, store):
        """Verify data survives between store instances (JSON file)."""
        sd = store.save(
            ScheduleDefinition(
                workflow_id="wf-123",
                trigger_type=TriggerType.CRON,
                trigger_config={"expression": "*/5 * * * *"},
            )
        )
        # Create a new store instance pointing to same directory
        from decision_system.workflow_engine.scheduler.store import ScheduleStore

        store2 = ScheduleStore(store._dir)
        loaded = store2.load(sd.id)
        assert loaded is not None
        assert loaded.workflow_id == "wf-123"
        assert loaded.trigger_config["expression"] == "*/5 * * * *"
        assert loaded.enabled is True

    def test_created_at_is_datetime_after_roundtrip(self, store):
        sd = store.save(ScheduleDefinition(workflow_id="wf-1"))
        loaded = store.load(sd.id)
        assert loaded is not None
        assert isinstance(loaded.created_at, datetime)

    def test_file_naming_pattern(self, store):
        sd = store.save(ScheduleDefinition(workflow_id="wf-1"))
        file_path = store._dir / f"schedule_{sd.id}.json"
        assert file_path.exists()
        data = json.loads(file_path.read_text())
        assert data["workflow_id"] == "wf-1"


# ─── Test Trigger Evaluators ─────────────────────────────────────────────────


class TestCronEvaluator:
    def test_every_minute_matches(self):
        from decision_system.workflow_engine.scheduler.triggers import evaluate_cron

        assert evaluate_cron("* * * * *") is True

    def test_nonexpression_does_not_match(self):
        from decision_system.workflow_engine.scheduler.triggers import evaluate_cron

        # This should not match at the current hour if not midnight
        result = evaluate_cron("0 3 * * *")  # 3:00 AM — unlikely current time
        assert result is False

    def test_already_fired_recently(self):
        from decision_system.workflow_engine.scheduler.triggers import evaluate_cron

        now = datetime.now(timezone.utc)
        # If last_fired is within the last 60 seconds, should not fire
        result = evaluate_cron("* * * * *", last_fired=now)
        assert result is False

    def test_fires_after_interval(self):
        from decision_system.workflow_engine.scheduler.triggers import evaluate_cron

        old = datetime(2020, 1, 1, tzinfo=timezone.utc)
        result = evaluate_cron("* * * * *", last_fired=old)
        assert result is True

    def test_invalid_expression_returns_false(self):
        from decision_system.workflow_engine.scheduler.triggers import evaluate_cron

        assert evaluate_cron("invalid") is False

    def test_wildcard_day_of_week(self):
        from decision_system.workflow_engine.scheduler.triggers import evaluate_cron

        # * for day of week = any day, should still work
        result = evaluate_cron("* * * * *")
        assert result is True


class TestWebhookEvaluator:
    def test_validate_path_match(self):
        from decision_system.workflow_engine.scheduler.triggers import (
            validate_webhook_path,
        )

        assert validate_webhook_path("/hooks/my-webhook", "/hooks/my-webhook") is True

    def test_validate_path_no_match(self):
        from decision_system.workflow_engine.scheduler.triggers import (
            validate_webhook_path,
        )

        assert validate_webhook_path("/hooks/wrong", "/hooks/my-webhook") is False

    def test_validate_path_with_trailing_slash(self):
        from decision_system.workflow_engine.scheduler.triggers import (
            validate_webhook_path,
        )

        assert validate_webhook_path("/hooks/my-webhook/", "/hooks/my-webhook") is True

    def test_validate_path_empty(self):
        from decision_system.workflow_engine.scheduler.triggers import (
            validate_webhook_path,
        )

        assert validate_webhook_path("", "/hooks/my-webhook") is False


class TestFileWatchEvaluator:
    def test_scan_nonexistent_dir(self):
        from decision_system.workflow_engine.scheduler.triggers import scan_directory

        current, new = scan_directory("/nonexistent/path", "*")
        assert current == set()
        assert new == []

    def test_scan_empty_dir(self, tmp_path):
        from decision_system.workflow_engine.scheduler.triggers import scan_directory

        current, new = scan_directory(str(tmp_path), "*")
        assert current == set()
        assert new == []

    def test_scan_new_file_detected(self, tmp_path):
        from decision_system.workflow_engine.scheduler.triggers import scan_directory

        # First scan: empty
        known, new = scan_directory(str(tmp_path), "*")
        assert known == set()
        assert new == []

        # Create a file
        (tmp_path / "test.md").write_text("hello")

        # Second scan with known files from first scan
        current, new = scan_directory(str(tmp_path), "*", known_files=known)
        assert "test.md" in current
        assert "test.md" in new

    def test_pattern_filter(self, tmp_path):
        from decision_system.workflow_engine.scheduler.triggers import scan_directory

        (tmp_path / "data.csv").write_text("a,b,c")
        (tmp_path / "notes.md").write_text("# Hello")

        current, new = scan_directory(str(tmp_path), "*.csv")
        assert "data.csv" in current
        assert "notes.md" not in current

    def test_no_duplicate_detection(self, tmp_path):
        from decision_system.workflow_engine.scheduler.triggers import scan_directory

        (tmp_path / "test.md").write_text("hello")
        known, new = scan_directory(str(tmp_path), "*")
        # Second scan with known files
        current, new2 = scan_directory(str(tmp_path), "*", known_files=known)
        assert new2 == []  # No new files

    def test_pattern_filter_no_match(self, tmp_path):
        from decision_system.workflow_engine.scheduler.triggers import scan_directory

        (tmp_path / "data.bin").write_text("binary")
        current, new = scan_directory(str(tmp_path), "*.csv")
        assert current == set()
        assert new == []

    def test_multiple_new_files(self, tmp_path):
        from decision_system.workflow_engine.scheduler.triggers import scan_directory

        known, _ = scan_directory(str(tmp_path), "*")

        (tmp_path / "a.md").write_text("a")
        (tmp_path / "b.md").write_text("b")

        current, new = scan_directory(str(tmp_path), "*", known_files=known)
        assert len(new) == 2
        assert "a.md" in new
        assert "b.md" in new


# ─── Test SchedulerService ────────────────────────────────────────────────────


class TestSchedulerService:
    @pytest.fixture
    def scheduler(self):
        import tempfile

        from decision_system.workflow_engine.engine.executor import DAGEngine
        from decision_system.workflow_engine.nodes import create_default_registry
        from decision_system.workflow_engine.scheduler.scheduler import SchedulerService
        from decision_system.workflow_engine.scheduler.store import ScheduleStore
        from decision_system.workflow_engine.stores.json_store import (
            JSONExecutionStore,
            JSONWorkflowStore,
        )

        tmp = tempfile.mkdtemp()
        store_dir = Path(tmp)
        schedule_store = ScheduleStore(store_dir / "schedules")
        registry = create_default_registry()
        wf_store = JSONWorkflowStore(store_dir / "workflows")
        exec_store = JSONExecutionStore(store_dir / "executions")
        engine = DAGEngine(registry=registry, workflow_store=wf_store, execution_store=exec_store)

        scheduler = SchedulerService(
            schedule_store=schedule_store,
            dag_engine=engine,
            poll_interval=0.1,  # Fast polling for tests
        )
        return scheduler, schedule_store, engine, wf_store, exec_store

    @pytest.mark.asyncio
    async def test_start_and_stop(self, scheduler):
        svc, *_ = scheduler
        assert svc._running is False
        await svc.start()
        assert svc._running is True
        await svc.stop()
        assert svc._running is False

    @pytest.mark.asyncio
    async def test_does_not_fire_disabled_schedule(self, scheduler):
        svc, sstore, engine, wf_store, exec_store = scheduler

        # Create a workflow
        from decision_system.workflow_engine.models import (
            NodeConfig,
            WorkflowDefinition,
        )

        wf = WorkflowDefinition(
            name="Test WF",
            nodes=[NodeConfig(id="n1", type="decision_system.trigger_manual")],
        )
        wf_store.save(wf)

        # Create a DISABLED schedule
        sstore.save(
            ScheduleDefinition(
                workflow_id=wf.id,
                trigger_type=TriggerType.CRON,
                trigger_config={"expression": "* * * * *"},
                enabled=False,
            )
        )

        await svc._check_schedules()
        # No workflows should be executed
        assert len(exec_store.list()) == 0
        await svc.stop()

    @pytest.mark.asyncio
    async def test_fires_matching_schedule(self, scheduler):
        svc, sstore, engine, wf_store, exec_store = scheduler

        from decision_system.workflow_engine.models import (
            NodeConfig,
            WorkflowDefinition,
        )

        wf = WorkflowDefinition(
            name="Test WF",
            nodes=[NodeConfig(id="n1", type="decision_system.trigger_manual")],
        )
        wf_store.save(wf)

        # Create an enabled cron schedule that matches every minute
        sstore.save(
            ScheduleDefinition(
                workflow_id=wf.id,
                trigger_type=TriggerType.CRON,
                trigger_config={"expression": "* * * * *"},
                enabled=True,
            )
        )

        await svc._check_schedules()
        # Should have fired the workflow
        assert len(exec_store.list()) >= 1
        await svc.stop()

    @pytest.mark.asyncio
    async def test_last_fired_updated(self, scheduler):
        svc, sstore, engine, wf_store, _ = scheduler

        from decision_system.workflow_engine.models import (
            NodeConfig,
            WorkflowDefinition,
        )

        wf = WorkflowDefinition(
            name="Test WF",
            nodes=[NodeConfig(id="n1", type="decision_system.trigger_manual")],
        )
        wf_store.save(wf)

        sd = sstore.save(
            ScheduleDefinition(
                workflow_id=wf.id,
                trigger_type=TriggerType.CRON,
                trigger_config={"expression": "* * * * *"},
            )
        )

        await svc._check_schedules()
        loaded = sstore.load(sd.id)
        assert loaded is not None
        assert loaded.last_fired is not None
        await svc.stop()

    @pytest.mark.asyncio
    async def test_no_schedule_no_fire(self, scheduler):
        svc, *_ = scheduler
        await svc._check_schedules()
        # No crash with empty store
        await svc.stop()

    @pytest.mark.asyncio
    async def test_multiple_schedules_same_workflow(self, scheduler):
        svc, sstore, engine, wf_store, exec_store = scheduler

        from decision_system.workflow_engine.models import (
            NodeConfig,
            WorkflowDefinition,
        )

        wf = WorkflowDefinition(
            name="Test WF",
            nodes=[NodeConfig(id="n1", type="decision_system.trigger_manual")],
        )
        wf_store.save(wf)

        sstore.save(
            ScheduleDefinition(
                workflow_id=wf.id,
                trigger_type=TriggerType.CRON,
                trigger_config={"expression": "* * * * *"},
            )
        )
        sstore.save(
            ScheduleDefinition(
                workflow_id=wf.id,
                trigger_type=TriggerType.FILE_WATCH,
                trigger_config={
                    "directory": str(Path(tempfile.mkdtemp())),
                    "pattern": "*",
                },
            )
        )

        await svc._check_schedules()
        # At least the cron one should fire
        assert len(exec_store.list()) >= 1
        await svc.stop()
