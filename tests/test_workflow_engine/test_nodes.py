"""Tests for node registry and base classes."""

import pytest

from decision_system.workflow_engine.models import (
    WorkflowNode, ExecutionContext, NodeTypeInfo,
)
from decision_system.workflow_engine.nodes.registry import NodeRegistry
from decision_system.workflow_engine.nodes.builtin.trigger_nodes import (
    ManualTriggerNode, InputTextNode,
)
from decision_system.workflow_engine.nodes.builtin.flow_nodes import (
    FilterNode, MergeNode, CodeNode,
)
from decision_system.workflow_engine.nodes.builtin.data_nodes import (
    ExtractGraphNode, ProfileDataNode, WarRoomNode,
)


class SimpleNode(WorkflowNode):
    """Minimal concrete node for testing."""

    type: str = "test.simple"
    label: str = "Simple Node"

    async def execute(self, inputs: dict, ctx: ExecutionContext) -> dict:
        return {"output": "hello"}

    @classmethod
    def get_config_schema(cls) -> dict:
        return {"type": "object", "properties": {}}

    @classmethod
    def get_input_schema(cls) -> dict:
        return {"type": "object", "properties": {"input": {"type": "string"}}}

    @classmethod
    def get_output_schema(cls) -> dict:
        return {"type": "object", "properties": {"output": {"type": "string"}}}


class TestNodeRegistry:
    def test_register_and_get(self):
        registry = NodeRegistry()
        registry.register(SimpleNode)
        node_cls = registry.get("test.simple")
        assert node_cls is SimpleNode

    def test_get_unknown_type(self):
        registry = NodeRegistry()
        with pytest.raises(KeyError, match="test.unknown"):
            registry.get("test.unknown")

    def test_list_types(self):
        registry = NodeRegistry()
        registry.register(SimpleNode)
        types = registry.list_types()
        assert len(types) == 1
        assert types[0].type == "test.simple"
        assert types[0].label == "Simple Node"

    def test_duplicate_registration_raises(self):
        registry = NodeRegistry()
        registry.register(SimpleNode)
        with pytest.raises(ValueError, match="already registered"):
            registry.register(SimpleNode)

    def test_get_node_type_info_includes_schemas(self):
        registry = NodeRegistry()
        registry.register(SimpleNode)
        info = registry.list_types()[0]
        assert info.config_schema == {"type": "object", "properties": {}}
        assert "input" in info.input_schema.get("properties", {})

    def test_instantiate_node_from_registry(self):
        registry = NodeRegistry()
        registry.register(SimpleNode)
        node = registry.instantiate("test.simple", id="n1")
        assert isinstance(node, SimpleNode)
        assert node.id == "n1"
        assert node.type == "test.simple"


class TestManualTriggerNode:
    @pytest.mark.asyncio
    async def test_trigger_passes_inputs(self):
        node = ManualTriggerNode(id="n1", type="decision_system.trigger_manual")
        ctx = ExecutionContext(workflow_id="wf1", execution_id="e1")
        result = await node.execute({"question": "test"}, ctx)
        assert result["triggered"] is True
        assert result["question"] == "test"


class TestInputTextNode:
    @pytest.mark.asyncio
    async def test_returns_configured_text(self):
        node = InputTextNode(
            id="n1", type="decision_system.input_text",
            config={"text": "What is our risk?"},
        )
        ctx = ExecutionContext(workflow_id="wf1", execution_id="e1")
        result = await node.execute({}, ctx)
        assert result["text"] == "What is our risk?"
        assert result["question"] == "What is our risk?"

    @pytest.mark.asyncio
    async def test_empty_text(self):
        node = InputTextNode(id="n1", type="decision_system.input_text")
        ctx = ExecutionContext(workflow_id="wf1", execution_id="e1")
        result = await node.execute({}, ctx)
        assert result["text"] == ""


class TestCodeNode:
    @pytest.mark.asyncio
    async def test_disabled_by_default(self):
        """CodeNode must raise RuntimeError when env var is not set."""
        import os
        os.environ.pop("DECISION_SYSTEM_ENABLE_UNSAFE_CODE_NODE", None)

        node = CodeNode(
            id="n1", type="decision_system.code",
            config={"source": "output = {'result': 42}"},
        )
        ctx = ExecutionContext(workflow_id="wf1", execution_id="e1")
        with pytest.raises(RuntimeError, match="disabled"):
            await node.execute({}, ctx)

    @pytest.mark.asyncio
    async def test_basic_code_execution(self):
        """CodeNode must work when env var enables it."""
        import os
        os.environ["DECISION_SYSTEM_ENABLE_UNSAFE_CODE_NODE"] = "true"

        node = CodeNode(
            id="n1", type="decision_system.code",
            config={"source": "output = {'result': inputs['value'] * 2}"},
        )
        ctx = ExecutionContext(workflow_id="wf1", execution_id="e1")
        result = await node.execute({"value": 21}, ctx)
        assert result["result"] == 42

    @pytest.mark.asyncio
    async def test_empty_code_passthrough(self):
        """CodeNode must passthrough inputs when enabled and no source."""
        import os
        os.environ["DECISION_SYSTEM_ENABLE_UNSAFE_CODE_NODE"] = "true"

        node = CodeNode(id="n1", type="decision_system.code")
        ctx = ExecutionContext(workflow_id="wf1", execution_id="e1")
        result = await node.execute({"key": "val"}, ctx)
        assert result == {"key": "val"}

    @pytest.mark.asyncio
    async def test_code_syntax_error(self):
        """CodeNode must raise on syntax errors when enabled."""
        import os
        os.environ["DECISION_SYSTEM_ENABLE_UNSAFE_CODE_NODE"] = "true"

        node = CodeNode(
            id="n1", type="decision_system.code",
            config={"source": "this is not valid python"},
        )
        ctx = ExecutionContext(workflow_id="wf1", execution_id="e1")
        with pytest.raises(Exception):
            await node.execute({}, ctx)


class TestFilterNode:
    @pytest.mark.asyncio
    async def test_equals_pass(self):
        node = FilterNode(
            id="n1", type="decision_system.filter",
            config={"field": "status", "operator": "equals", "value": "active"},
        )
        ctx = ExecutionContext(workflow_id="wf1", execution_id="e1")
        result = await node.execute({"status": "active"}, ctx)
        assert result["passed"] is True

    @pytest.mark.asyncio
    async def test_equals_fail(self):
        node = FilterNode(
            id="n1", type="decision_system.filter",
            config={"field": "status", "operator": "equals", "value": "inactive"},
        )
        ctx = ExecutionContext(workflow_id="wf1", execution_id="e1")
        result = await node.execute({"status": "active"}, ctx)
        assert result["passed"] is False


class TestMergeNode:
    @pytest.mark.asyncio
    async def test_merge_strategy(self):
        node = MergeNode(
            id="n1", type="decision_system.merge",
            config={"strategy": "merge"},
        )
        ctx = ExecutionContext(workflow_id="wf1", execution_id="e1")
        result = await node.execute({"a": 1, "b": 2}, ctx)
        assert result["a"] == 1
        assert result["b"] == 2


class TestExtractGraphNode:
    @pytest.mark.asyncio
    async def test_empty_chunks(self):
        node = ExtractGraphNode(id="n1", type="decision_system.extract_graph")
        ctx = ExecutionContext(workflow_id="wf1", execution_id="e1")
        result = await node.execute({"chunks": []}, ctx)
        assert result["entity_count"] == 0


class TestProfileDataNode:
    @pytest.mark.asyncio
    async def test_nonexistent_catalog(self):
        node = ProfileDataNode(
            id="n1", type="decision_system.profile_data",
            config={"catalog_path": "/tmp/nonexistent_catalog_xyz"},
        )
        ctx = ExecutionContext(workflow_id="wf1", execution_id="e1")
        result = await node.execute({}, ctx)
        assert result["count"] == 0


class TestWarRoomNode:
    @pytest.mark.asyncio
    async def test_empty_question(self):
        node = WarRoomNode(id="n1", type="decision_system.war_room")
        ctx = ExecutionContext(workflow_id="wf1", execution_id="e1")
        result = await node.execute({}, ctx)
        assert result["artifact_count"] >= 0


class TestDefaultRegistry:
    def test_create_default_registry_contains_all_builtins(self):
        from decision_system.workflow_engine.nodes import create_default_registry
        registry = create_default_registry()
        types = registry.list_types()
        type_names = {t.type for t in types}
        assert "decision_system.trigger_manual" in type_names
        assert "decision_system.retrieve" in type_names
        assert "decision_system.technical_analyst" in type_names
        assert "decision_system.risk_analyst" in type_names
        assert "decision_system.extract_claims" in type_names
        assert "decision_system.verify_claims" in type_names
        assert "decision_system.write_report" in type_names
        assert "decision_system.extract_graph" in type_names
        assert "decision_system.profile_data" in type_names
        assert "decision_system.map_ontology" in type_names
        assert "decision_system.detect_patterns" in type_names
        assert "decision_system.war_room" in type_names
        assert "decision_system.input_text" in type_names
        assert "decision_system.filter" in type_names
        assert "decision_system.merge" in type_names
        assert "decision_system.code" in type_names
        assert "decision_system.researcher" in type_names
        assert "decision_system.critic" in type_names
        assert "decision_system.synthesizer" in type_names
        assert "decision_system.data_analyst" in type_names
        assert "decision_system.review_gate" in type_names
        assert "decision_system.planner" in type_names
        assert "decision_system.auditor" in type_names
        assert "decision_system.compliance_checker" in type_names
        assert "decision_system.code_runner" in type_names
        assert len(type_names) == 37
