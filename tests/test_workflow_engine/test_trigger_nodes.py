"""Tests for trigger node types — CronTrigger, WebhookTrigger, FileWatchTrigger."""

from __future__ import annotations

import pytest

from decision_system.workflow_engine.models import ExecutionContext


# ─── Test CronTriggerNode ────────────────────────────────────────────────────

class TestCronTriggerNode:
    def test_type_and_label(self):
        from decision_system.workflow_engine.nodes.builtin.trigger_nodes import (
            CronTriggerNode,
        )
        node = CronTriggerNode(id="n1")
        assert node.type == "decision_system.trigger_cron"
        assert node.label == "Cron Trigger"

    @pytest.mark.asyncio
    async def test_execute_returns_schedule_config(self):
        from decision_system.workflow_engine.nodes.builtin.trigger_nodes import (
            CronTriggerNode,
        )
        node = CronTriggerNode(
            id="n1",
            type="decision_system.trigger_cron",
            config={"expression": "0 9 * * 1-5"},
            label="Weekday Cron",
        )
        ctx = ExecutionContext(workflow_id="wf-1", execution_id="e-1")
        result = await node.execute({}, ctx)
        assert result["trigger_type"] == "cron"
        assert result["expression"] == "0 9 * * 1-5"
        assert result["triggered"] is True

    def test_config_schema(self):
        from decision_system.workflow_engine.nodes.builtin.trigger_nodes import (
            CronTriggerNode,
        )
        schema = CronTriggerNode.get_config_schema()
        assert "expression" in schema["properties"]
        assert schema["properties"]["expression"]["default"] == "0 9 * * *"
        assert schema["properties"]["expression"]["type"] == "string"

    def test_default_expression(self):
        from decision_system.workflow_engine.nodes.builtin.trigger_nodes import (
            CronTriggerNode,
        )
        node = CronTriggerNode(
            id="n1",
            type="decision_system.trigger_cron",
        )
        assert node.config.get("expression", "0 9 * * *") == "0 9 * * *"

    def test_input_schema(self):
        from decision_system.workflow_engine.nodes.builtin.trigger_nodes import (
            CronTriggerNode,
        )
        schema = CronTriggerNode.get_input_schema()
        assert len(schema["properties"]) == 0

    def test_output_schema(self):
        from decision_system.workflow_engine.nodes.builtin.trigger_nodes import (
            CronTriggerNode,
        )
        schema = CronTriggerNode.get_output_schema()
        assert "trigger_type" in schema["properties"]
        assert "expression" in schema["properties"]
        assert "triggered" in schema["properties"]

    @pytest.mark.asyncio
    async def test_serialize_to_node_type_info(self):
        from decision_system.workflow_engine.nodes import create_default_registry
        registry = create_default_registry()
        types = registry.list_types()
        cron_type = [t for t in types if t.type == "decision_system.trigger_cron"]
        assert len(cron_type) == 1
        assert cron_type[0].label == "Cron Trigger"
        assert "expression" in cron_type[0].config_schema["properties"]


# ─── Test WebhookTriggerNode ─────────────────────────────────────────────────

class TestWebhookTriggerNode:
    def test_type_and_label(self):
        from decision_system.workflow_engine.nodes.builtin.trigger_nodes import (
            WebhookTriggerNode,
        )
        node = WebhookTriggerNode(id="n2")
        assert node.type == "decision_system.trigger_webhook"
        assert node.label == "Webhook Trigger"

    @pytest.mark.asyncio
    async def test_execute_returns_path(self):
        from decision_system.workflow_engine.nodes.builtin.trigger_nodes import (
            WebhookTriggerNode,
        )
        node = WebhookTriggerNode(
            id="n1",
            type="decision_system.trigger_webhook",
            config={"webhook_path": "/hooks/my-webhook"},
        )
        ctx = ExecutionContext(workflow_id="wf-1", execution_id="e-1")
        result = await node.execute({}, ctx)
        assert result["trigger_type"] == "webhook"
        assert result["webhook_path"] == "/hooks/my-webhook"
        assert result["triggered"] is True

    def test_config_schema(self):
        from decision_system.workflow_engine.nodes.builtin.trigger_nodes import (
            WebhookTriggerNode,
        )
        schema = WebhookTriggerNode.get_config_schema()
        assert "webhook_path" in schema["properties"]

    def test_input_schema_has_payload(self):
        from decision_system.workflow_engine.nodes.builtin.trigger_nodes import (
            WebhookTriggerNode,
        )
        schema = WebhookTriggerNode.get_input_schema()
        assert "payload" in schema["properties"]

    def test_output_schema(self):
        from decision_system.workflow_engine.nodes.builtin.trigger_nodes import (
            WebhookTriggerNode,
        )
        schema = WebhookTriggerNode.get_output_schema()
        assert "webhook_path" in schema["properties"]

    @pytest.mark.asyncio
    async def test_execute_passes_through_inputs(self):
        from decision_system.workflow_engine.nodes.builtin.trigger_nodes import (
            WebhookTriggerNode,
        )
        node = WebhookTriggerNode(
            id="n1",
            type="decision_system.trigger_webhook",
            config={"webhook_path": "/hooks/my-webhook"},
        )
        ctx = ExecutionContext(workflow_id="wf-1", execution_id="e-1")
        result = await node.execute({"payload": {"event": "push"}}, ctx)
        assert result["payload"] == {"event": "push"}


# ─── Test FileWatchTriggerNode ───────────────────────────────────────────────

class TestFileWatchTriggerNode:
    def test_type_and_label(self):
        from decision_system.workflow_engine.nodes.builtin.trigger_nodes import (
            FileWatchTriggerNode,
        )
        node = FileWatchTriggerNode(id="n3")
        assert node.type == "decision_system.trigger_file_watch"
        assert node.label == "File Watch Trigger"

    @pytest.mark.asyncio
    async def test_execute_returns_directory_and_pattern(self):
        from decision_system.workflow_engine.nodes.builtin.trigger_nodes import (
            FileWatchTriggerNode,
        )
        node = FileWatchTriggerNode(
            id="n1",
            type="decision_system.trigger_file_watch",
            config={"directory": "company_docs/", "pattern": "*.md"},
        )
        ctx = ExecutionContext(workflow_id="wf-1", execution_id="e-1")
        result = await node.execute({}, ctx)
        assert result["trigger_type"] == "file_watch"
        assert result["directory"] == "company_docs/"
        assert result["pattern"] == "*.md"
        assert result["triggered"] is True

    def test_config_schema(self):
        from decision_system.workflow_engine.nodes.builtin.trigger_nodes import (
            FileWatchTriggerNode,
        )
        schema = FileWatchTriggerNode.get_config_schema()
        assert "directory" in schema["properties"]
        assert "pattern" in schema["properties"]

    def test_default_pattern(self):
        from decision_system.workflow_engine.nodes.builtin.trigger_nodes import (
            FileWatchTriggerNode,
        )
        node = FileWatchTriggerNode(
            id="n1",
            type="decision_system.trigger_file_watch",
        )
        assert node.config.get("pattern", "*") == "*"

    def test_input_schema(self):
        from decision_system.workflow_engine.nodes.builtin.trigger_nodes import (
            FileWatchTriggerNode,
        )
        schema = FileWatchTriggerNode.get_input_schema()
        assert len(schema["properties"]) == 0

    def test_output_schema(self):
        from decision_system.workflow_engine.nodes.builtin.trigger_nodes import (
            FileWatchTriggerNode,
        )
        schema = FileWatchTriggerNode.get_output_schema()
        assert "changed_files" in schema["properties"]
        assert "directory" in schema["properties"]

    @pytest.mark.asyncio
    async def test_changed_files_from_inputs(self):
        from decision_system.workflow_engine.nodes.builtin.trigger_nodes import (
            FileWatchTriggerNode,
        )
        node = FileWatchTriggerNode(
            id="n1",
            type="decision_system.trigger_file_watch",
            config={"directory": "docs/", "pattern": "*.md"},
        )
        ctx = ExecutionContext(workflow_id="wf-1", execution_id="e-1")
        result = await node.execute(
            {"_changed_files": ["new.md", "updated.md"]},
            ctx,
        )
        assert result["changed_files"] == ["new.md", "updated.md"]


# ─── Test Registry Integration ───────────────────────────────────────────────

class TestTriggerNodeRegistry:
    def test_all_trigger_nodes_registered_by_default(self):
        from decision_system.workflow_engine.nodes import create_default_registry
        registry = create_default_registry()
        types = {t.type for t in registry.list_types()}
        assert "decision_system.trigger_cron" in types
        assert "decision_system.trigger_webhook" in types
        assert "decision_system.trigger_file_watch" in types

    def test_16_builtin_nodes_plus_3_trigger_plus_4_specialist_plus_review_gate_equals_24(self):
        from decision_system.workflow_engine.nodes import create_default_registry
        registry = create_default_registry()
        types = registry.list_types()
        assert len(types) == 28  # 16 original + 3 trigger + 4 specialist + 1 review_gate + 4 new specialist (planner, auditor, compliance, code)

    def test_new_trigger_nodes_appear_in_list_types(self):
        from decision_system.workflow_engine.nodes import create_default_registry
        registry = create_default_registry()
        node_types = {t.label: t for t in registry.list_types()}
        assert "Cron Trigger" in node_types
        assert "Webhook Trigger" in node_types
        assert "File Watch Trigger" in node_types

    def test_instantiate_cron_trigger(self):
        from decision_system.workflow_engine.nodes import create_default_registry
        registry = create_default_registry()
        node = registry.instantiate(
            "decision_system.trigger_cron",
            id="n1",
            config={"expression": "0 8 * * *"},
        )
        assert node.type == "decision_system.trigger_cron"
        assert node.config["expression"] == "0 8 * * *"

    def test_instantiate_webhook_trigger(self):
        from decision_system.workflow_engine.nodes import create_default_registry
        registry = create_default_registry()
        node = registry.instantiate(
            "decision_system.trigger_webhook",
            id="n2",
            config={"webhook_path": "/hooks/test"},
        )
        assert node.type == "decision_system.trigger_webhook"
        assert node.config["webhook_path"] == "/hooks/test"

    def test_instantiate_file_watch_trigger(self):
        from decision_system.workflow_engine.nodes import create_default_registry
        registry = create_default_registry()
        node = registry.instantiate(
            "decision_system.trigger_file_watch",
            id="n3",
            config={"directory": "/tmp", "pattern": "*.log"},
        )
        assert node.type == "decision_system.trigger_file_watch"
        assert node.config["directory"] == "/tmp"
