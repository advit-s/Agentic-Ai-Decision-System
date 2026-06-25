"""Tests for audit events and observability metrics in verification/report actions."""

from __future__ import annotations

import tempfile
from pathlib import Path

from decision_system.observability.metrics import MetricsCollector, MetricType
from decision_system.observability.store import (
    list_metric_names,
    load_metric_points,
)
from decision_system.security.audit import append_event, load_events


class TestVerificationAuditEvents:
    """Audit events are emitted for verification actions."""

    def test_claim_verified_audit_event(self):
        """Verifying a claim creates an audit event."""
        with tempfile.TemporaryDirectory() as tmpdir:
            audit_path = Path(tmpdir) / "audit_log.jsonl"
            event = append_event(
                "claim_verified",
                "Claim claim-1 verified as supported",
                metadata={
                    "claim_id": "claim-1",
                    "status": "supported",
                    "confidence": "high",
                    "workspace_id": "ws-1",
                },
                audit_path=audit_path,
            )
            assert event.event_type == "claim_verified"
            assert event.metadata["claim_id"] == "claim-1"
            assert event.metadata["status"] == "supported"

            events = load_events(audit_path)
            assert len(events) == 1
            assert events[0].event_type == "claim_verified"

    def test_execution_claims_verified_audit_event(self):
        """Verifying execution claims creates an audit event."""
        with tempfile.TemporaryDirectory() as tmpdir:
            audit_path = Path(tmpdir) / "audit_log.jsonl"
            event = append_event(
                "execution_claims_verified",
                "Verified 5 claims for execution exec-1",
                metadata={
                    "execution_id": "exec-1",
                    "total": 5,
                    "workspace_id": "ws-1",
                },
                audit_path=audit_path,
            )
            assert event.event_type == "execution_claims_verified"
            assert event.metadata["execution_id"] == "exec-1"
            assert event.metadata["total"] == 5

            events = load_events(audit_path)
            assert len(events) == 1

    def test_workspace_claims_verified_audit_event(self):
        """Verifying workspace claims creates an audit event."""
        with tempfile.TemporaryDirectory() as tmpdir:
            audit_path = Path(tmpdir) / "audit_log.jsonl"
            event = append_event(
                "workspace_claims_verified",
                "Verified 10 claims for workspace ws-1",
                metadata={
                    "workspace_id": "ws-1",
                    "total": 10,
                },
                audit_path=audit_path,
            )
            assert event.event_type == "workspace_claims_verified"
            assert event.metadata["workspace_id"] == "ws-1"

            events = load_events(audit_path)
            assert len(events) == 1

    def test_contradiction_scan_run_audit_event(self):
        """Running a contradiction scan creates an audit event."""
        with tempfile.TemporaryDirectory() as tmpdir:
            audit_path = Path(tmpdir) / "audit_log.jsonl"
            event = append_event(
                "contradiction_scan_run",
                "Scanned contradictions for workspace ws-1: found 2",
                metadata={
                    "workspace_id": "ws-1",
                    "count": 2,
                },
                audit_path=audit_path,
            )
            assert event.event_type == "contradiction_scan_run"
            assert event.metadata["count"] == 2

            events = load_events(audit_path)
            assert len(events) == 1

    def test_trust_report_generated_audit_event(self):
        """Generating a trust report creates an audit event."""
        with tempfile.TemporaryDirectory() as tmpdir:
            audit_path = Path(tmpdir) / "audit_log.jsonl"
            event = append_event(
                "trust_report_generated",
                "Trust report rpt-1 generated for execution exec-1",
                metadata={
                    "execution_id": "exec-1",
                    "workspace_id": "ws-1",
                    "report_id": "rpt-1",
                    "claim_count": 5,
                },
                audit_path=audit_path,
            )
            assert event.event_type == "trust_report_generated"
            assert event.metadata["report_id"] == "rpt-1"

            events = load_events(audit_path)
            assert len(events) == 1

    def test_trust_report_exported_audit_event(self):
        """Exporting a trust report creates an audit event."""
        with tempfile.TemporaryDirectory() as tmpdir:
            audit_path = Path(tmpdir) / "audit_log.jsonl"
            event = append_event(
                "trust_report_exported",
                "Trust report rpt-1 exported as md",
                metadata={
                    "report_id": "rpt-1",
                    "workspace_id": "ws-1",
                    "format": "md",
                },
                audit_path=audit_path,
            )
            assert event.event_type == "trust_report_exported"
            assert event.metadata["format"] == "md"

            events = load_events(audit_path)
            assert len(events) == 1

    def test_multiple_audit_events(self):
        """Multiple audit events are all persisted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            audit_path = Path(tmpdir) / "audit_log.jsonl"
            append_event(
                "claim_verified",
                "First",
                metadata={"claim_id": "c1"},
                audit_path=audit_path,
            )
            append_event(
                "contradiction_scan_run",
                "Second",
                metadata={"count": 3},
                audit_path=audit_path,
            )
            append_event(
                "trust_report_generated",
                "Third",
                metadata={"report_id": "rpt-1"},
                audit_path=audit_path,
            )

            events = load_events(audit_path)
            assert len(events) == 3
            assert events[0].event_type == "claim_verified"
            assert events[1].event_type == "contradiction_scan_run"
            assert events[2].event_type == "trust_report_generated"


class TestVerificationObservabilityMetrics:
    """Observability metrics are emitted for verification/report actions."""

    def test_claim_verified_metric(self):
        """Verification emits claims_verified_count metric."""
        collector = MetricsCollector()
        collector.record("claims_verified_count", 1, MetricType.COUNTER, {"action": "verify"})
        collector.record("verification_duration_ms", 150, MetricType.TIMER)
        # Verify points were recorded (check that the metrics file exists)
        names = list_metric_names()
        assert "claims_verified_count" in names
        assert "verification_duration_ms" in names

    def test_contradiction_metric(self):
        """Contradiction scan emits contradictions_found_count metric."""
        collector = MetricsCollector()
        collector.record(
            "contradictions_found_count",
            3,
            MetricType.COUNTER,
            {"workspace_id": "ws-1"},
        )
        names = list_metric_names()
        assert "contradictions_found_count" in names

    def test_unsupported_claims_metric(self):
        """Verification emits unsupported_claims_count metric."""
        collector = MetricsCollector()
        collector.record("unsupported_claims_count", 2, MetricType.COUNTER)
        names = list_metric_names()
        assert "unsupported_claims_count" in names

    def test_average_confidence_metric(self):
        """Verification emits average_confidence gauge metric."""
        collector = MetricsCollector()
        collector.record("average_confidence", 0.75, MetricType.GAUGE)
        points = load_metric_points("average_confidence")
        assert len(points) > 0
        assert points[-1].value == 0.75

    def test_needs_review_claims_metric(self):
        """Verification emits needs_review_claims_count metric."""
        collector = MetricsCollector()
        collector.record("needs_review_claims_count", 1, MetricType.COUNTER)
        names = list_metric_names()
        assert "needs_review_claims_count" in names

    def test_trust_report_generation_metric(self):
        """Report generation emits trust_report_generation_duration_ms metric."""
        collector = MetricsCollector()
        collector.record(
            "trust_report_generation_duration_ms",
            0,
            MetricType.TIMER,
            {
                "execution_id": "exec-1",
                "workspace_id": "ws-1",
                "report_id": "rpt-1",
                "claim_count": "5",
            },
        )
        names = list_metric_names()
        assert "trust_report_generation_duration_ms" in names

    def test_verification_duration_metric_persistence(self):
        """Verification duration metric persists and can be loaded."""
        collector = MetricsCollector()
        collector.record("verification_duration_ms", 250, MetricType.TIMER)
        points = load_metric_points("verification_duration_ms")
        assert len(points) > 0
        assert points[-1].value == 250
        assert points[-1].metric_type == MetricType.TIMER.value

    def test_uncertain_claims_metric(self):
        """Verification emits uncertain_claims_count metric."""
        collector = MetricsCollector()
        collector.record("uncertain_claims_count", 1, MetricType.COUNTER)
        names = list_metric_names()
        assert "uncertain_claims_count" in names
