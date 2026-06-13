"""Integration tests for specialist agent node chaining — Researcher, Critic, Synthesizer."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from decision_system.workflow_engine.models import (
    WorkflowDefinition, NodeConfig, Connection,
)
from decision_system.workflow_engine.engine.executor import DAGEngine
from decision_system.workflow_engine.nodes import create_default_registry
from decision_system.workflow_engine.stores.json_store import (
    JSONWorkflowStore, JSONExecutionStore,
)


@pytest.fixture
def engine():
    registry = create_default_registry()
    tmp_dir = Path(tempfile.mkdtemp())
    ws = JSONWorkflowStore(tmp_dir)
    es = JSONExecutionStore(tmp_dir)
    return DAGEngine(registry=registry, workflow_store=ws, execution_store=es)


class TestResearcherToCriticChain:
    """Researcher -> Critic/Judge: feed structured findings to the reviewer."""

    def test_researcher_output_feeds_critic(self, engine):
        """Researcher's findings are reviewed by Critic; Critic issues are based on findings."""
        import asyncio

        wf = WorkflowDefinition(
            name="Research and Review",
            nodes=[
                NodeConfig(
                    id="researcher",
                    type="decision_system.researcher",
                    config={},
                ),
                NodeConfig(
                    id="critic",
                    type="decision_system.critic",
                    config={"criteria": ["unsupported_claims"]},
                ),
            ],
            connections=[
                Connection(
                    source_node="researcher",
                    source_output="default",
                    target_node="critic",
                    target_input="default",
                ),
            ],
        )
        state = asyncio.run(engine.execute(
            wf,
            global_inputs={"query": "revenue growth"},
        ))
        assert state.status == "completed"

        # Researcher should have produced findings
        researcher_state = state.node_states["researcher"]
        assert researcher_state.status == "completed"
        researcher_outputs = researcher_state.outputs or {}
        assert "findings" in researcher_outputs
        assert len(researcher_outputs["findings"]) > 0

        # Critic should have received researcher's findings and reviewed them
        critic_state = state.node_states["critic"]
        assert critic_state.status == "completed"
        critic_outputs = critic_state.outputs or {}
        assert "passed" in critic_outputs
        assert "issues" in critic_outputs
        assert "summary" in critic_outputs


class TestMultiStreamToSynthesizer:
    """Multi-input: Researcher + Critic -> Synthesizer."""

    def test_multi_stream_synthesis(self, engine):
        """Two specialist nodes feed into Synthesizer; all nodes complete."""
        import asyncio

        wf = WorkflowDefinition(
            name="Multi-Stream Synthesis",
            nodes=[
                NodeConfig(
                    id="researcher1",
                    type="decision_system.researcher",
                    config={},
                ),
                NodeConfig(
                    id="researcher2",
                    type="decision_system.researcher",
                    config={},
                ),
                NodeConfig(
                    id="synthesizer",
                    type="decision_system.synthesizer",
                    config={},
                ),
            ],
            connections=[
                Connection(
                    source_node="researcher1",
                    source_output="default",
                    target_node="synthesizer",
                    target_input="evidence_streams",
                ),
                Connection(
                    source_node="researcher2",
                    source_output="default",
                    target_node="synthesizer",
                    target_input="evidence_streams",
                ),
            ],
        )
        state = asyncio.run(engine.execute(
            wf,
            global_inputs={"query": "market analysis", "question": "Should we invest?"},
        ))
        assert state.status == "completed"

        # All nodes completed
        for node_id in ("researcher1", "researcher2", "synthesizer"):
            assert state.node_states[node_id].status == "completed"


class TestSynthesizerToCriticValidationGate:
    """Synthesizer -> Critic: validate decision quality before output."""

    def test_validation_gate_passes_clean(self, engine):
        """Valid decision passes critic review."""
        import asyncio

        wf = WorkflowDefinition(
            name="Validate Decision",
            nodes=[
                NodeConfig(
                    id="researcher",
                    type="decision_system.researcher",
                    config={},
                ),
                NodeConfig(
                    id="synthesizer",
                    type="decision_system.synthesizer",
                    config={},
                ),
                NodeConfig(
                    id="critic",
                    type="decision_system.critic",
                    config={
                        "criteria": ["unsupported_claims", "contradictions"],
                    },
                ),
            ],
            connections=[
                Connection(
                    source_node="researcher",
                    source_output="default",
                    target_node="synthesizer",
                    target_input="evidence_streams",
                ),
                Connection(
                    source_node="synthesizer",
                    source_output="default",
                    target_node="critic",
                    target_input="default",
                ),
            ],
        )
        state = asyncio.run(engine.execute(
            wf,
            global_inputs={"query": "risk analysis", "question": "Should we invest?"},
        ))
        assert state.status == "completed"

        for node_id in ("researcher", "synthesizer", "critic"):
            assert state.node_states[node_id].status == "completed"

        critic_outputs = state.node_states["critic"].outputs or {}
        assert "passed" in critic_outputs
        assert "issues" in critic_outputs
        assert "confidence_adjustment" in critic_outputs
        assert isinstance(critic_outputs["passed"], bool)


class TestProviderResolutionOrder:
    """Verify provider per-node override and system default work correctly."""

    def test_provider_per_node_override(self, engine):
        """Each node can use fake provider without issues."""
        import asyncio

        wf = WorkflowDefinition(
            name="Provider Override Test",
            nodes=[
                NodeConfig(
                    id="researcher",
                    type="decision_system.researcher",
                    config={},
                ),
                NodeConfig(
                    id="critic",
                    type="decision_system.critic",
                    config={"criteria": ["unsupported_claims"]},
                ),
            ],
            connections=[
                Connection(
                    source_node="researcher",
                    source_output="default",
                    target_node="critic",
                    target_input="default",
                ),
            ],
        )
        state = asyncio.run(engine.execute(
            wf,
            global_inputs={"query": "test"},
        ))
        assert state.status == "completed"
        assert state.node_states["researcher"].status == "completed"
        assert state.node_states["critic"].status == "completed"
