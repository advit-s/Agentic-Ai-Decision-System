"""Tests for v1.3 Observability and Evaluation History.

All tests are offline/local. No external services or API keys required.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from decision_system.observability.models import (
    EvalRunRecord,
    EvalStatus,
    MetricPoint,
    MetricSummary,
    MetricType,
    QualityDimension,
    QualityReport,
    TraceSummary,
)
from decision_system.observability.store import (
    compute_metric_summary,
    get_paths,
    init_store,
    list_metric_names,
    load_eval_runs,
    load_metric_points,
    load_quality_reports,
    load_traces,
    save_eval_run,
    save_metric_point,
    save_quality_report,
    save_trace,
)
from decision_system.observability.metrics import MetricsCollector, MetricsReporter
from decision_system.observability.eval_history import EvalHistory
from decision_system.observability.quality_report import (
    generate_quality_report,
    quality_report_summary_json,
)
from decision_system.observability.trace_summary import create_trace, get_recent_traces
from decision_system.observability.inspector import print_observability_summary


# ================================================================
# Models
# ================================================================


class TestModels:
    def test_metric_point(self) -> None:
        p = MetricPoint(name="latency", value=1.5, metric_type=MetricType.TIMER)
        assert p.name == "latency"
        assert p.value == 1.5
        assert p.metric_type == MetricType.TIMER

    def test_metric_summary(self) -> None:
        s = MetricSummary(name="latency", count=10, sum=15.0, min=1.0, max=2.0, avg=1.5)
        assert s.avg == 1.5
        assert s.count == 10

    def test_eval_run_record(self) -> None:
        r = EvalRunRecord(
            eval_type="local",
            status=EvalStatus.PASSED,
            started_at=datetime.now(timezone.utc),
            total_cases=3,
            passed_cases=3,
        )
        assert r.run_id
        assert r.eval_type == "local"

    def test_quality_report(self) -> None:
        q = QualityReport(
            target_type="eval_run",
            target_id="t1",
            overall_score=0.9,
            overall_status="pass",
        )
        assert q.overall_score == 0.9

    def test_trace_summary(self) -> None:
        t = TraceSummary(
            workflow_type="decision",
            question="test?",
            started_at=datetime.now(timezone.utc),
        )
        assert t.workflow_type == "decision"
        assert t.error_count == 0

    def test_eval_status_values(self) -> None:
        assert EvalStatus.PASSED.value == "passed"
        assert EvalStatus.FAILED.value == "failed"

    def test_metric_type_values(self) -> None:
        assert MetricType.COUNTER.value == "counter"
        assert MetricType.TIMER.value == "timer"

    def test_quality_dimension_values(self) -> None:
        assert QualityDimension.CORRECTNESS.value == "correctness"
        assert QualityDimension.HALLUCINATION_RISK.value == "hallucination_risk"


# ================================================================
# Store
# ================================================================


class TestStore:
    def test_init_store(self, tmp_path: Path) -> None:
        paths = init_store(str(tmp_path / "obs"))
        assert Path(paths.root).exists()
        assert Path(paths.metrics).exists()
        assert Path(paths.eval_history).exists()
        assert Path(paths.quality_reports).exists()
        assert Path(paths.traces).exists()

    def test_save_and_load_metric(self, tmp_path: Path) -> None:
        root = str(tmp_path / "obs")
        init_store(root)
        point = MetricPoint(
            name="latency", value=1.5, metric_type=MetricType.TIMER,
            timestamp=datetime.now(timezone.utc), labels={"provider": "fake"},
        )
        save_metric_point(point, root)
        points = load_metric_points("latency", root)
        assert len(points) == 1
        assert points[0].value == 1.5
        assert points[0].labels["provider"] == "fake"

    def test_list_metric_names(self, tmp_path: Path) -> None:
        root = str(tmp_path / "obs")
        init_store(root)
        p1 = MetricPoint(name="a", value=1.0, metric_type=MetricType.COUNTER)
        p2 = MetricPoint(name="b", value=2.0, metric_type=MetricType.COUNTER)
        save_metric_point(p1, root)
        save_metric_point(p2, root)
        names = list_metric_names(root)
        assert "a" in names
        assert "b" in names

    def test_compute_metric_summary(self, tmp_path: Path) -> None:
        root = str(tmp_path / "obs")
        init_store(root)
        for v in [1.0, 2.0, 3.0, 4.0, 5.0]:
            save_metric_point(
                MetricPoint(name="x", value=v, metric_type=MetricType.COUNTER),
                root,
            )
        summary = compute_metric_summary("x", root)
        assert summary is not None
        assert summary.count == 5
        assert summary.min == 1.0
        assert summary.max == 5.0
        assert summary.avg == pytest.approx(3.0)

    def test_compute_metric_summary_empty(self, tmp_path: Path) -> None:
        root = str(tmp_path / "obs")
        init_store(root)
        assert compute_metric_summary("nonexistent", root) is None

    def test_save_and_load_eval_run(self, tmp_path: Path) -> None:
        root = str(tmp_path / "obs")
        init_store(root)
        record = EvalRunRecord(
            eval_type="local",
            status=EvalStatus.PASSED,
            started_at=datetime.now(timezone.utc),
            total_cases=5,
            passed_cases=5,
        )
        save_eval_run(record, root)
        runs = load_eval_runs(root)
        assert len(runs) == 1
        assert runs[0].run_id == record.run_id
        assert runs[0].eval_type == "local"

    def test_save_and_load_quality_report(self, tmp_path: Path) -> None:
        root = str(tmp_path / "obs")
        init_store(root)
        report = QualityReport(
            target_type="eval_run",
            target_id="test",
            overall_score=0.85,
            overall_status="pass",
        )
        save_quality_report(report, root)
        reports = load_quality_reports(root)
        assert len(reports) == 1
        assert reports[0].overall_score == 0.85

    def test_save_and_load_trace(self, tmp_path: Path) -> None:
        root = str(tmp_path / "obs")
        init_store(root)
        trace = TraceSummary(
            workflow_type="decision",
            question="test q?",
            started_at=datetime.now(timezone.utc),
            node_count=5,
        )
        save_trace(trace, root)
        traces = load_traces(root)
        assert len(traces) == 1
        assert traces[0].workflow_type == "decision"

    def test_load_empty_dirs(self, tmp_path: Path) -> None:
        root = str(tmp_path / "obs_empty")
        assert load_eval_runs(root) == []
        assert load_quality_reports(root) == []
        assert load_traces(root) == []
        assert list_metric_names(root) == []


# ================================================================
# Metrics Collector
# ================================================================


class TestMetricsCollector:
    def test_record_and_persist(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        import decision_system.observability.store as store_mod

        root = str(tmp_path / "obs")
        init_store(root)
        monkeypatch.setenv("DECISION_OBSERVABILITY_ROOT", root)
        monkeypatch.setattr(store_mod, "_get_default_root", lambda: root)

        collector = MetricsCollector()
        collector.record("latency", 1.5, MetricType.TIMER, {"provider": "fake"})
        points = load_metric_points("latency", root)
        assert len(points) == 1
        assert points[0].value == 1.5

    def test_reporter(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        import decision_system.observability.store as store_mod

        root = str(tmp_path / "obs")
        init_store(root)
        monkeypatch.setattr(store_mod, "_get_default_root", lambda: root)

        collector = MetricsCollector()
        collector.record("x", 1.0, MetricType.COUNTER)
        collector.record("x", 2.0, MetricType.COUNTER)

        reporter = MetricsReporter()
        summaries = reporter.report()
        assert any(s.name == "x" for s in summaries)


# ================================================================
# Eval History
# ================================================================


class TestEvalHistory:
    def test_record_and_get(self, tmp_path: Path) -> None:
        root = str(tmp_path / "obs")
        init_store(root)
        history = EvalHistory(root)
        record = EvalRunRecord(
            eval_type="provider",
            status=EvalStatus.PASSED,
            started_at=datetime.now(timezone.utc),
            total_cases=8,
            passed_cases=8,
        )
        run_id = history.record_run(record)
        assert run_id == record.run_id
        fetched = history.get_run(run_id)
        assert fetched is not None
        assert fetched.eval_type == "provider"

    def test_get_all_runs(self, tmp_path: Path) -> None:
        root = str(tmp_path / "obs")
        init_store(root)
        history = EvalHistory(root)
        history.record_run(
            EvalRunRecord(
                eval_type="a",
                status=EvalStatus.PASSED,
                started_at=datetime.now(timezone.utc),
            )
        )
        history.record_run(
            EvalRunRecord(
                eval_type="b",
                status=EvalStatus.FAILED,
                started_at=datetime.now(timezone.utc),
            )
        )
        assert len(history.get_all_runs()) == 2

    def test_summary(self, tmp_path: Path) -> None:
        root = str(tmp_path / "obs")
        init_store(root)
        history = EvalHistory(root)
        history.record_run(
            EvalRunRecord(
                eval_type="test",
                status=EvalStatus.PASSED,
                started_at=datetime.now(timezone.utc),
                total_cases=10,
                passed_cases=10,
                duration_seconds=5.0,
            )
        )
        summary = history.get_summary()
        assert summary["total_runs"] == 1
        assert summary["passed_runs"] == 1
        assert summary["total_cases"] == 10


# ================================================================
# Quality Report Generator
# ================================================================


class TestQualityReportGenerator:
    def test_no_runs(self, tmp_path: Path) -> None:
        root = str(tmp_path / "obs")
        init_store(root)
        report = generate_quality_report(root=root)
        assert report.overall_score == 0.0
        assert report.overall_status == "pass"
        assert len(report.recommendations) > 0

    def test_with_passing_run(self, tmp_path: Path) -> None:
        root = str(tmp_path / "obs")
        init_store(root)
        save_eval_run(
            EvalRunRecord(
                eval_type="local",
                status=EvalStatus.PASSED,
                started_at=datetime.now(timezone.utc),
                total_cases=10,
                passed_cases=9,
                failed_cases=1,
            ),
            root,
        )
        report = generate_quality_report(root=root)
        assert report.overall_score == 0.9
        assert report.overall_status == "pass"

    def test_json_summary(self) -> None:
        report = QualityReport(
            target_type="eval_run",
            target_id="t1",
            overall_score=0.75,
            overall_status="warn",
        )
        j = quality_report_summary_json(report)
        assert j["overall_score"] == 0.75
        assert j["overall_status"] == "warn"


# ================================================================
# Trace Summary
# ================================================================


class TestTraceSummary:
    def test_create_trace(self, tmp_path: Path) -> None:
        root = str(tmp_path / "obs")
        init_store(root)
        now = datetime.now(timezone.utc)
        trace = create_trace(
            workflow_type="decision",
            question="What is risk?",
            started_at=now,
            completed_at=now + timedelta(seconds=3),
            node_count=6,
            root=root,
        )
        assert trace.duration_seconds == pytest.approx(3.0)
        assert trace.node_count == 6

    def test_get_recent_traces(self, tmp_path: Path) -> None:
        root = str(tmp_path / "obs")
        init_store(root)
        now = datetime.now(timezone.utc)
        create_trace(
            "decision", "q1", now, root=root,
        )
        create_trace(
            "war_room", "q2", now, root=root,
        )
        traces = get_recent_traces(limit=1, root=root)
        assert len(traces) == 1


# ================================================================
# Inspector
# ================================================================


class TestInspector:
    def test_json_summary(self, tmp_path: Path) -> None:
        import decision_system.observability.store as store_mod

        root = str(tmp_path / "obs")
        init_store(root)
        monkeypatch_set = {}
        # Patch the store module's _get_default_root
        import decision_system.observability.inspector as inspector_mod
        # We need the store functions used by inspector to use our root
        # Simplest: save some data with root explicitly
        save_eval_run(
            EvalRunRecord(
                eval_type="local",
                status=EvalStatus.PASSED,
                started_at=datetime.now(timezone.utc),
                total_cases=3,
                passed_cases=3,
            ),
            root,
        )
        # Test print_observability_summary with json=True - it uses load_* from store
        # which uses default root. We'll test the json mode works without patched root
        result = print_observability_summary(as_json=True)
        assert "metrics" in result
        assert "eval_runs" in result
        assert "traces" in result
        assert "quality_reports" in result
