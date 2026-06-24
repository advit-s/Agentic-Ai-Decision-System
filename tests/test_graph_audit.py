"""Tests for the graph audit/observability module (Phase 16)."""

from __future__ import annotations

import time

import pytest

from decision_system.graphing.audit import (
    graph_extraction_completed,
    graph_extraction_failed,
    graph_extraction_started,
    graph_fact_created,
    metric_extraction_completed,
    risk_extraction_completed,
    track_graph_extraction,
)
from decision_system.observability.store import (
    get_paths,
    list_metric_names,
    load_metric_points,
)


@pytest.fixture(autouse=True)
def _clean_metrics():
    """Clean up any test metric data before and after."""
    import shutil
    paths = get_paths()
    try:
        shutil.rmtree(paths.metrics)
    except FileNotFoundError:
        pass
    yield
    try:
        shutil.rmtree(paths.metrics)
    except FileNotFoundError:
        pass


class TestGraphAuditEvents:
    """Tests for graph audit event helpers."""

    def test_graph_extraction_started_records_event(self):
        graph_extraction_started("ws-1")
        names = list_metric_names()
        assert "graph_extraction_started" in names

    def test_graph_extraction_started_has_labels(self):
        graph_extraction_started("ws-1", extra_info="test")
        points = load_metric_points("graph_extraction_started")
        assert len(points) >= 1
        assert points[0].labels.get("workspace_id") == "ws-1"

    def test_graph_extraction_completed_records_events(self):
        graph_extraction_completed(
            workspace_id="ws-1",
            duration_ms=150.0,
            entities_count=5,
            edges_count=3,
            risks_count=2,
            metrics_count=4,
        )
        names = list_metric_names()
        assert "graph_extraction_completed" in names
        assert "graph_extraction_duration_ms" in names
        assert "entities_extracted_count" in names

    def test_graph_extraction_completed_has_correct_values(self):
        graph_extraction_completed("ws-1", duration_ms=200.0)
        points = load_metric_points("graph_extraction_duration_ms")
        assert len(points) >= 1
        assert points[0].value == pytest.approx(200.0, rel=0.1)

    def test_graph_extraction_failed_records_event(self):
        graph_extraction_failed("ws-1", "Connection error")
        names = list_metric_names()
        assert "graph_extraction_failed" in names
        assert "graph_extraction_failure_count" in names

    def test_graph_extraction_failed_includes_error_label(self):
        graph_extraction_failed("ws-1", "Timeout")
        points = load_metric_points("graph_extraction_failed")
        assert len(points) >= 1
        assert "error" in points[0].labels
        assert points[0].labels.get("error") == "Timeout"

    def test_risk_extraction_completed_records_event(self):
        risk_extraction_completed("ws-1", risks_count=3)
        names = list_metric_names()
        assert "risk_extraction_completed" in names
        assert "risks_extracted_count" in names

    def test_metric_extraction_completed_records_event(self):
        metric_extraction_completed("ws-1", metrics_count=5)
        names = list_metric_names()
        assert "metric_extraction_completed" in names
        assert "metrics_extracted_count" in names

    def test_graph_fact_created_records_event(self):
        graph_fact_created("ws-1", fact_type="node", fact_id="node-acme")
        names = list_metric_names()
        assert "graph_fact_created" in names
        points = load_metric_points("graph_fact_created")
        assert points[0].labels.get("fact_type") == "node"
        assert points[0].labels.get("fact_id") == "node-acme"

    def test_graph_fact_created_truncates_long_ids(self):
        long_id = "a" * 100
        graph_fact_created("ws-1", fact_type="edge", fact_id=long_id)
        points = load_metric_points("graph_fact_created")
        assert len(points[0].labels.get("fact_id", "")) <= 40

    def test_track_graph_extraction_context_success(self):
        with track_graph_extraction("ws-ctx") as state:
            state["entities"] = 10
            state["edges"] = 5
            state["risks"] = 2
            state["metrics"] = 3

        names = list_metric_names()
        assert "graph_extraction_started" in names
        assert "graph_extraction_completed" in names
        assert "entities_extracted_count" in names

        # Verify entity count
        ent_points = load_metric_points("entities_extracted_count")
        assert len(ent_points) >= 1
        # The exact value could be accumulated across multiple metric points
        total = sum(p.value for p in ent_points)
        assert total >= 10

    def test_track_graph_extraction_context_failure(self):
        """Context manager should emit failure event on exception."""
        try:
            with track_graph_extraction("ws-fail") as state:
                state["entities"] = 5
                raise ValueError("Something went wrong")
        except ValueError:
            pass

        names = list_metric_names()
        assert "graph_extraction_started" in names
        assert "graph_extraction_failed" in names
        assert "graph_extraction_failure_count" in names

    def test_track_graph_extraction_emits_duration(self):
        with track_graph_extraction("ws-dur") as state:
            state["entities"] = 1
            time.sleep(0.01)  # Small delay to ensure duration > 0

        dur_points = load_metric_points("graph_extraction_duration_ms")
        assert len(dur_points) >= 1
        assert dur_points[0].value > 0

    def test_multiple_events_accumulate(self):
        """Multiple graph events should be recorded independently."""
        graph_extraction_started("ws-multi")
        graph_extraction_started("ws-multi")

        points = load_metric_points("graph_extraction_started")
        assert len(points) >= 2

    def test_empty_completion_no_crash(self):
        """Completion with zero counts should not crash."""
        graph_extraction_completed("ws-zero", duration_ms=0.0)
        assert True  # No crash

    def test_all_event_types_registered(self):
        """All required event types should be recordable."""
        graph_extraction_started("ws-all")
        graph_extraction_completed("ws-all", duration_ms=100.0)
        graph_extraction_failed("ws-all", "error")
        risk_extraction_completed("ws-all")
        metric_extraction_completed("ws-all")
        graph_fact_created("ws-all", fact_type="risk", fact_id="r1")

        names = list_metric_names()
        required = [
            "graph_extraction_started",
            "graph_extraction_completed",
            "graph_extraction_failed",
            "risk_extraction_completed",
            "metric_extraction_completed",
            "graph_fact_created",
            "graph_extraction_duration_ms",
            "graph_extraction_failure_count",
        ]
        for name in required:
            assert name in names, f"Missing metric: {name}"
