"""Tests for DAG validation and topological sort."""

import pytest
from uuid import UUID

from decision_system.workflow_engine.models import (
    WorkflowDefinition, NodeConfig, Connection, ErrorPolicy,
)
from decision_system.workflow_engine.engine.dag import (
    DAGValidator, TopologicalSort, DAGError,
    CyclicDAGError, MissingConnectionError,
)


def _make_wf(nodes: list[dict], connections: list[dict]) -> WorkflowDefinition:
    return WorkflowDefinition(
        id=str(UUID(int=0)),
        name="test",
        nodes=[NodeConfig(**n) for n in nodes],
        connections=[Connection(**c) for c in connections],
    )


class TestDAGError:
    def test_base_error(self):
        err = DAGError("something went wrong")
        assert str(err) == "something went wrong"
        assert isinstance(err, Exception)


class TestDAGValidator:
    def test_empty_workflow_valid(self):
        wf = _make_wf([], [])
        errors = DAGValidator.validate(wf)
        assert errors == []

    def test_single_node_valid(self):
        wf = _make_wf(
            [{"id": "n1", "type": "test"}],
            [],
        )
        errors = DAGValidator.validate(wf)
        assert errors == []

    def test_linear_chain_valid(self):
        wf = _make_wf(
            [{"id": "n1", "type": "test"}, {"id": "n2", "type": "test"}],
            [{"source_node": "n1", "target_node": "n2"}],
        )
        errors = DAGValidator.validate(wf)
        assert errors == []

    def test_self_loop_invalid(self):
        wf = _make_wf(
            [{"id": "n1", "type": "test"}],
            [{"source_node": "n1", "target_node": "n1"}],
        )
        errors = DAGValidator.validate(wf)
        assert len(errors) == 1
        assert isinstance(errors[0], CyclicDAGError)

    def test_cycle_invalid(self):
        wf = _make_wf(
            [
                {"id": "n1", "type": "test"},
                {"id": "n2", "type": "test"},
                {"id": "n3", "type": "test"},
            ],
            [
                {"source_node": "n1", "target_node": "n2"},
                {"source_node": "n2", "target_node": "n3"},
                {"source_node": "n3", "target_node": "n1"},
            ],
        )
        errors = DAGValidator.validate(wf)
        assert len(errors) == 1
        assert isinstance(errors[0], CyclicDAGError)

    def test_missing_source_node(self):
        wf = _make_wf(
            [{"id": "n1", "type": "test"}],
            [{"source_node": "n2", "target_node": "n1"}],
        )
        errors = DAGValidator.validate(wf)
        assert len(errors) == 1
        assert isinstance(errors[0], MissingConnectionError)
        assert "n2" in str(errors[0])

    def test_missing_target_node(self):
        wf = _make_wf(
            [{"id": "n1", "type": "test"}],
            [{"source_node": "n1", "target_node": "n3"}],
        )
        errors = DAGValidator.validate(wf)
        assert len(errors) == 1
        assert isinstance(errors[0], MissingConnectionError)
        assert "n3" in str(errors[0])

    def test_multiple_errors(self):
        """A cycle and a missing node should both be reported."""
        wf = _make_wf(
            [{"id": "n1", "type": "test"}, {"id": "n2", "type": "test"}],
            [
                {"source_node": "n1", "target_node": "n2"},
                {"source_node": "n2", "target_node": "n1"},
                {"source_node": "missing", "target_node": "n1"},
            ],
        )
        errors = DAGValidator.validate(wf)
        assert len(errors) == 2


class TestTopologicalSort:
    def test_empty(self):
        layers = TopologicalSort.sort(WorkflowDefinition(name="test"))
        assert layers == []

    def test_single_node(self):
        wf = _make_wf(
            [{"id": "n1", "type": "test"}],
            [],
        )
        layers = TopologicalSort.sort(wf)
        assert layers == [["n1"]]

    def test_linear_chain(self):
        wf = _make_wf(
            [{"id": "n1", "type": "test"}, {"id": "n2", "type": "test"}],
            [{"source_node": "n1", "target_node": "n2"}],
        )
        layers = TopologicalSort.sort(wf)
        assert layers == [["n1"], ["n2"]]

    def test_diamond_dag(self):
        """n1 feeds n2 and n3, both feed n4."""
        wf = _make_wf(
            [
                {"id": "n1", "type": "test"},
                {"id": "n2", "type": "test"},
                {"id": "n3", "type": "test"},
                {"id": "n4", "type": "test"},
            ],
            [
                {"source_node": "n1", "target_node": "n2"},
                {"source_node": "n1", "target_node": "n3"},
                {"source_node": "n2", "target_node": "n4"},
                {"source_node": "n3", "target_node": "n4"},
            ],
        )
        layers = TopologicalSort.sort(wf)
        # n1 must be first; n2 and n3 in same layer; n4 last
        assert layers[0] == ["n1"]
        assert set(layers[1]) == {"n2", "n3"}
        assert layers[2] == ["n4"]

    def test_independent_branches(self):
        """n1 -> n2 and n3 -> n4. n1/n3 are layer 0; n2/n4 layer 1."""
        wf = _make_wf(
            [
                {"id": "n1", "type": "test"},
                {"id": "n2", "type": "test"},
                {"id": "n3", "type": "test"},
                {"id": "n4", "type": "test"},
            ],
            [
                {"source_node": "n1", "target_node": "n2"},
                {"source_node": "n3", "target_node": "n4"},
            ],
        )
        layers = TopologicalSort.sort(wf)
        # Layer 0: {n1, n3} (no deps), Layer 1: {n2, n4}
        assert set(layers[0]) == {"n1", "n3"}
        assert set(layers[1]) == {"n2", "n4"}

    def test_disconnected_nodes(self):
        """Two nodes with no connection should both be in layer 0."""
        wf = _make_wf(
            [{"id": "n1", "type": "test"}, {"id": "n2", "type": "test"}],
            [],
        )
        layers = TopologicalSort.sort(wf)
        assert set(layers[0]) == {"n1", "n2"}

    def test_three_layer_dag(self):
        wf = _make_wf(
            [
                {"id": "n1", "type": "test"},
                {"id": "n2", "type": "test"},
                {"id": "n3", "type": "test"},
            ],
            [
                {"source_node": "n1", "target_node": "n2"},
                {"source_node": "n2", "target_node": "n3"},
            ],
        )
        layers = TopologicalSort.sort(wf)
        assert layers == [["n1"], ["n2"], ["n3"]]
