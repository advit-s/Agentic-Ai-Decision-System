"""Tests for the deterministic insight engine (v0.4)."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import pytest

from decision_system.data_catalog.models import (
    ColumnProfile,
    DataProfileStore,
    DataCategory,
    DatasetProfile,
)
from decision_system.graphing.models import (
    Entity,
    EntityType,
    KnowledgeGraph,
    Relationship,
    RelationType,
)
from decision_system.insights.detectors import run_detectors
from decision_system.insights.inspector import inspect_insights, render_insight_inspection
from decision_system.insights.models import (
    Insight,
    InsightCategory,
    InsightStore,
    InsightSeverity,
)
from decision_system.insights.store import load_insights, save_insights
from typer.testing import CliRunner

from decision_system.cli import app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_row(**kwargs: Any) -> dict[str, str]:
    return {k: str(v) for k, v in kwargs.items()}


def _profile_with(
    filename: str = "demo_financials.csv",
    category: DataCategory = "financial",
    row_count: int = 5,
    columns: list[ColumnProfile] | None = None,
    warnings: list[str] | None = None,
) -> DatasetProfile:
    return DatasetProfile(
        dataset_id="demo_financials",
        category=category,
        filename=filename,
        row_count=row_count,
        column_count=len(columns or []),
        columns=columns or [],
        warnings=warnings or [],
    )


def _write_csv(
    data_root: Path,
    category: str,
    filename: str,
    rows: list[dict[str, Any]],
    headers: list[str],
) -> Path:
    path = data_root / category / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
    return path


# ---------------------------------------------------------------------------
# Insight model tests
# ---------------------------------------------------------------------------


class TestInsightModel:
    def test_insight_roundtrip(self):
        insight = Insight(
            insight_id="test:abc",
            title="Revenue risk",
            description="Expenses are too high",
            category="revenue_risk",
            severity="high",
            confidence="high",
            source_type="csv",
            source_ids=["demo_financials"],
            evidence_summary="Average expense/revenue ratio is 0.92",
            recommended_action="Review cost structure",
        )
        payload = insight.model_dump(mode="json")
        assert payload["insight_id"] == "test:abc"
        assert payload["severity"] == "high"
        assert payload["category"] == "revenue_risk"
        restored = Insight.model_validate(payload)
        assert restored == insight

    def test_insight_default_values(self):
        insight = Insight(insight_id="x:1", title="T")
        assert insight.description == ""
        assert insight.category == "unknown"
        assert insight.severity == "medium"
        assert insight.source_ids == []
        assert insight.created_at

    def test_insight_store_add_and_counts(self):
        store = InsightStore()
        assert store.insights == []
        insight_a = Insight(
            insight_id="a:1", title="A", category="missing_data", severity="high"
        )
        insight_b = Insight(
            insight_id="b:1", title="B", category="data_quality", severity="medium"
        )
        store.add(insight_a)
        store.add(insight_b)
        assert len(store.insights) == 2
        assert store.severity_counts() == {"high": 1, "medium": 1}
        assert store.category_counts() == {
            "missing_data": 1,
            "data_quality": 1,
        }

    def test_insight_store_deduplication(self):
        store = InsightStore()
        first = Insight(
            insight_id="x:1", title="Same title", category="missing_data", severity="medium"
        )
        duplicate = Insight(
            insight_id="x:1", title="Different title", category="missing_data", severity="high"
        )
        store.add(first)
        store.add(duplicate)
        assert len(store.insights) == 1
        assert store.insights[0].severity == "high"


# ---------------------------------------------------------------------------
# Store persistence tests
# ---------------------------------------------------------------------------


class TestInsightStore:
    def test_save_and_load_roundtrip(self, tmp_path: Path):
        store = InsightStore(
            insights=[
                Insight(
                    insight_id="test:1",
                    title="Test insight",
                    category="missing_data",
                    severity="high",
                )
            ]
        )
        insight_dir = tmp_path / "insights_out"
        saved = save_insights(store, insight_dir)
        assert saved.exists()
        loaded = load_insights(insight_dir)
        assert len(loaded.insights) == 1
        assert loaded.insights[0].insight_id == "test:1"
        assert loaded.insights[0].title == "Test insight"

    def test_load_missing_returns_empty(self, tmp_path: Path):
        store = load_insights(tmp_path / "nonexistent")
        assert store.insights == []
        assert isinstance(store, InsightStore)

    def test_save_creates_parent_dirs(self, tmp_path: Path):
        store = InsightStore()
        deep = tmp_path / "a" / "b" / "c"
        save_insights(store, deep)
        assert (deep / "insights.json").exists()


# ---------------------------------------------------------------------------
# Inspector tests
# ---------------------------------------------------------------------------


class TestInspector:
    def test_inspect_insights_basic(self):
        store = InsightStore(
            insights=[
                Insight(insight_id="a:1", title="A", category="missing_data", severity="high"),
                Insight(insight_id="b:1", title="B", category="data_quality", severity="medium"),
                Insight(insight_id="c:1", title="C", category="missing_data", severity="medium"),
            ]
        )
        summary = inspect_insights(store)
        assert summary["total_insights"] == 3
        assert summary["severity_counts"]["high"] == 1
        assert summary["severity_counts"]["medium"] == 2
        assert summary["category_counts"]["missing_data"] == 2
        assert summary["category_counts"]["data_quality"] == 1
        assert len(summary["top_insights"]) == 3

    def test_inspect_insights_empty(self):
        summary = inspect_insights(InsightStore())
        assert summary["total_insights"] == 0
        assert summary["severity_counts"] == {}
        assert summary["category_counts"] == {}
        assert summary["top_insights"] == []

    def test_render_inspection_empty(self):
        output = render_insight_inspection(inspect_insights(InsightStore()))
        assert "Total insights: 0" in output

    def test_render_inspection_with_data(self):
        store = InsightStore(
            insights=[
                Insight(
                    insight_id="x:1",
                    title="Test insight",
                    category="missing_data",
                    severity="critical",
                )
            ]
        )
        output = render_insight_inspection(inspect_insights(store))
        assert "Total insights: 1" in output
        assert "CRITICAL" in output
        assert "missing_data" in output


# ---------------------------------------------------------------------------
# Profile-based detectors
# ---------------------------------------------------------------------------


class TestMissingDataDetector:
    def test_medium_missing_creates_insight(self):
        col = ColumnProfile(
            name="email", missing_count=3, missing_pct=0.30, unique_count=10
        )
        profile = _profile_with(
            filename="customers.csv",
            category="customers",
            columns=[col],
            row_count=10,
        )
        store = run_detectors(profiles=DataProfileStore(profiles=[profile]))
        assert len(store.insights) == 1
        ins = store.insights[0]
        assert ins.category == "missing_data"
        assert ins.severity == "medium"
        assert "customers.csv" in ins.title
        assert "email" in ins.title

    def test_high_missing_creates_high_severity(self):
        col = ColumnProfile(
            name="notes", missing_count=6, missing_pct=0.60, unique_count=2
        )
        profile = _profile_with(columns=[col], row_count=10)
        store = run_detectors(profiles=DataProfileStore(profiles=[profile]))
        assert store.insights[0].severity == "high"

    def test_below_threshold_no_insight(self):
        col = ColumnProfile(
            name="email", missing_count=1, missing_pct=0.10, unique_count=9
        )
        profile = _profile_with(columns=[col], row_count=10)
        store = run_detectors(profiles=DataProfileStore(profiles=[profile]))
        assert not any(i.category == "missing_data" for i in store.insights)


class TestDataQualityDetector:
    def test_warnings_create_insight(self):
        profile = _profile_with(
            warnings=["Column 'x' is >50% missing", "Row 5: field count mismatch"]
        )
        store = run_detectors(profiles=DataProfileStore(profiles=[profile]))
        assert len(store.insights) == 1
        ins = store.insights[0]
        assert ins.category == "data_quality"
        assert ins.severity in ("low", "medium")

    def test_no_warnings_no_insight(self):
        profile = _profile_with(warnings=[])
        store = run_detectors(profiles=DataProfileStore(profiles=[profile]))
        assert len(store.insights) == 0

    def test_large_warning_count_high_severity(self):
        warns = [f"Warning {i}" for i in range(10)]
        profile = _profile_with(warnings=warns)
        store = run_detectors(profiles=DataProfileStore(profiles=[profile]))
        assert store.insights[0].severity == "high"


class TestSalesChannelConcentration:
    def test_above_60pct_creates_medium(self):
        col = ColumnProfile(
            name="lead_source",
            missing_count=0,
            missing_pct=0.0,
            unique_count=3,
            top_values=[("Organic", 7), ("Paid", 2), ("Social", 1)],
        )
        profile = _profile_with(
            filename="demo_sales.csv",
            category="sales",
            columns=[col],
            row_count=10,
        )
        store = run_detectors(profiles=DataProfileStore(profiles=[profile]))
        assert len(store.insights) == 1
        ins = store.insights[0]
        assert ins.category == "sales_channel_risk"
        assert "Organic" in ins.title
        assert ins.severity == "medium"

    def test_above_80pct_creates_high(self):
        col = ColumnProfile(
            name="lead_source",
            missing_count=0,
            missing_pct=0.0,
            unique_count=2,
            top_values=[("Paid", 17), ("Organic", 3)],
        )
        profile = _profile_with(
            filename="demo_sales.csv",
            category="sales",
            columns=[col],
            row_count=20,
        )
        store = run_detectors(profiles=DataProfileStore(profiles=[profile]))
        assert store.insights[0].severity == "high"

    def test_below_threshold_no_insight(self):
        col = ColumnProfile(
            name="lead_source",
            missing_count=0,
            missing_pct=0.0,
            unique_count=3,
            top_values=[("Organic", 5), ("Paid", 3), ("Social", 2)],
        )
        profile = _profile_with(
            filename="demo_sales.csv",
            category="sales",
            columns=[col],
            row_count=10,
        )
        store = run_detectors(profiles=DataProfileStore(profiles=[profile]))
        assert not any(i.category == "sales_channel_risk" for i in store.insights)


class TestCustomerConcentration:
    def test_above_50pct_creates_insight(self):
        col = ColumnProfile(
            name="segment",
            missing_count=0,
            missing_pct=0.0,
            unique_count=3,
            top_values=[("enterprise", 13), ("smb", 7), ("startup", 4)],
        )
        profile = _profile_with(
            filename="demo_customers.csv",
            category="customers",
            columns=[col],
            row_count=24,
        )
        store = run_detectors(profiles=DataProfileStore(profiles=[profile]))
        assert len(store.insights) == 1
        ins = store.insights[0]
        assert ins.category == "customer_concentration"
        assert "enterprise" in ins.title


# ---------------------------------------------------------------------------
# Business CSV detectors
# ---------------------------------------------------------------------------


class TestRevenueRisk:
    def test_high_expense_ratio_creates_insight(self, tmp_path: Path):
        rows = [
            _make_row(
                month="2025-01", product="Vertex", revenue="12000", expenses="11850"
            ),
            _make_row(
                month="2025-02", product="Vertex", revenue="12000", expenses="11200"
            ),
        ]
        headers = ["month", "product", "revenue", "expenses"]
        _write_csv(tmp_path, "financial", "demo_financials.csv", rows, headers)

        col_rev = ColumnProfile(
            name="revenue",
            missing_count=0,
            missing_pct=0.0,
            unique_count=len(rows),
            numeric_summary={
                "min": 12000.0,
                "max": 12000.0,
                "mean": 12000.0,
                "median": 12000.0,
            },
        )
        col_exp = ColumnProfile(
            name="expenses",
            missing_count=0,
            missing_pct=0.0,
            unique_count=len(rows),
            numeric_summary={
                "min": 11200.0,
                "max": 11850.0,
                "mean": 11525.0,
                "median": 11525.0,
            },
        )
        profile = _profile_with(
            filename="demo_financials.csv",
            category="financial",
            row_count=len(rows),
            columns=[col_rev, col_exp],
        )
        store = run_detectors(
            profiles=DataProfileStore(profiles=[profile]),
            csv_root=tmp_path,
        )
        revenue_insights = [i for i in store.insights if i.category == "revenue_risk"]
        assert len(revenue_insights) >= 1
        assert revenue_insights[0].source_type == "csv"

    def test_low_margin_creates_profit_margin_risk(self, tmp_path: Path):
        rows = [_make_row(month="2025-01", revenue="1000", expenses="950", profit_margin="0.05")]
        headers = ["month", "revenue", "expenses", "profit_margin"]
        _write_csv(tmp_path, "financial", "demo_financials.csv", rows, headers)

        col_margin = ColumnProfile(
            name="profit_margin",
            missing_count=0,
            missing_pct=0.0,
            unique_count=1,
            numeric_summary={"min": 0.05, "max": 0.05, "mean": 0.05, "median": 0.05},
        )
        profile = _profile_with(
            filename="demo_financials.csv",
            category="financial",
            row_count=1,
            columns=[col_margin],
        )
        store = run_detectors(
            profiles=DataProfileStore(profiles=[profile]),
            csv_root=tmp_path,
        )
        margin_insights = [
            i for i in store.insights if i.category == "profit_margin_risk"
        ]
        assert len(margin_insights) >= 1

    def test_no_risk_when_csv_missing(self, tmp_path: Path):
        col_rev = ColumnProfile(
            name="revenue",
            missing_count=0,
            missing_pct=0.0,
            unique_count=1,
            numeric_summary={"min": 1000.0, "max": 1000.0, "mean": 1000.0, "median": 1000.0},
        )
        col_exp = ColumnProfile(
            name="expenses",
            missing_count=0,
            missing_pct=0.0,
            unique_count=1,
            numeric_summary={"min": 500.0, "max": 500.0, "mean": 500.0, "median": 500.0},
        )
        profile = _profile_with(columns=[col_rev, col_exp])
        store = run_detectors(profiles=DataProfileStore(profiles=[profile]), csv_root=tmp_path)
        assert not any(i.category == "revenue_risk" for i in store.insights)


class TestMarketingROI:
    def test_low_roas_creates_insight(self, tmp_path: Path):
        rows = [
            _make_row(
                month="2025-01",
                channel="TikTok",
                spend="1200",
                clicks="9600",
                conversions="15",
                revenue="600",
            ),
        ]
        headers = ["month", "channel", "spend", "clicks", "conversions", "revenue"]
        _write_csv(tmp_path, "marketing", "demo_marketing.csv", rows, headers)

        col_spend = ColumnProfile(
            name="spend",
            missing_count=0,
            missing_pct=0.0,
            unique_count=1,
            numeric_summary={"min": 1200.0, "max": 1200.0, "mean": 1200.0, "median": 1200.0},
        )
        col_rev = ColumnProfile(
            name="revenue",
            missing_count=0,
            missing_pct=0.0,
            unique_count=1,
            numeric_summary={"min": 600.0, "max": 600.0, "mean": 600.0, "median": 600.0},
        )
        col_conv = ColumnProfile(
            name="conversions",
            missing_count=0,
            missing_pct=0.0,
            unique_count=1,
            numeric_summary={"min": 15.0, "max": 15.0, "mean": 15.0, "median": 15.0},
        )
        profile = _profile_with(
            filename="demo_marketing.csv",
            category="marketing",
            row_count=1,
            columns=[col_spend, col_rev, col_conv],
        )
        store = run_detectors(
            profiles=DataProfileStore(profiles=[profile]),
            csv_root=tmp_path,
        )
        roi_insights = [i for i in store.insights if i.category == "marketing_roi_risk"]
        assert len(roi_insights) >= 1
        assert roi_insights[0].severity == "medium"


class TestCustomerConcentrationCSV:
    def test_customer_concentration_from_csv(self, tmp_path: Path):
        rows = [
            _make_row(city="NY", segment="enterprise", signup_month="2025-01", lifetime_value="5000")
            for _ in range(8)
        ]
        rows += [
            _make_row(city="Austin", segment="smb", signup_month="2025-01", lifetime_value="3000")
            for _ in range(4)
        ]
        rows += [
            _make_row(city="Seattle", segment="startup", signup_month="2025-01", lifetime_value="2000")
            for _ in range(3)
        ]
        headers = ["city", "segment", "signup_month", "lifetime_value"]
        _write_csv(tmp_path, "customers", "demo_customers.csv", rows, headers)

        col_seg = ColumnProfile(
            name="segment",
            missing_count=0,
            missing_pct=0.0,
            unique_count=3,
            top_values=[("enterprise", 8), ("smb", 4), ("startup", 3)],
        )
        profile = _profile_with(
            filename="demo_customers.csv",
            category="customers",
            row_count=len(rows),
            columns=[col_seg],
        )
        store = run_detectors(
            profiles=DataProfileStore(profiles=[profile]),
            csv_root=tmp_path,
        )
        conc = [i for i in store.insights if i.category == "customer_concentration"]
        assert len(conc) >= 1
        assert "enterprise" in conc[0].title


class TestSalesChannelConcentrationCSV:
    def test_sales_channel_concentration_from_csv(self, tmp_path: Path):
        rows = [
            _make_row(month="2025-01", product="A", region="N", sales_amount="100", lead_source="Organic")
            for _ in range(7)
        ]
        rows += [
            _make_row(month="2025-01", product="A", region="N", sales_amount="200", lead_source="Paid")
            for _ in range(3)
        ]
        headers = ["month", "product", "region", "sales_amount", "lead_source"]
        _write_csv(tmp_path, "sales", "demo_sales.csv", rows, headers)

        col_source = ColumnProfile(
            name="lead_source",
            missing_count=0,
            missing_pct=0.0,
            unique_count=2,
            top_values=[("Organic", 7), ("Paid", 3)],
        )
        profile = _profile_with(
            filename="demo_sales.csv",
            category="sales",
            row_count=10,
            columns=[col_source],
        )
        store = run_detectors(
            profiles=DataProfileStore(profiles=[profile]),
            csv_root=tmp_path,
        )
        channel_insights = [i for i in store.insights if i.category == "sales_channel_risk"]
        assert len(channel_insights) >= 1


# ---------------------------------------------------------------------------
# Graph-based detectors
# ---------------------------------------------------------------------------


class TestGraphDetectors:
    def _make_graph(self, entities, relationships):
        return KnowledgeGraph(entities=entities, relationships=relationships)

    def test_dependency_risk_two_incoming(self):
        e1 = Entity(
            entity_id="e-billing", name="Billing", entity_type="system",
            confidence="medium",
        )
        e2 = Entity(
            entity_id="e-auth", name="Auth", entity_type="system",
            confidence="medium",
        )
        e3 = Entity(
            entity_id="e-db", name="Database", entity_type="system",
            confidence="medium",
        )
        rels = [
            Relationship(
                relationship_id="r1",
                source_entity_id=e1.entity_id,
                relation_type="depends_on",
                target_entity_id=e3.entity_id,
                confidence="medium",
            ),
            Relationship(
                relationship_id="r2",
                source_entity_id=e2.entity_id,
                relation_type="depends_on",
                target_entity_id=e3.entity_id,
                confidence="medium",
            ),
        ]
        store = run_detectors(graph=self._make_graph([e1, e2, e3], rels))
        deps = [i for i in store.insights if i.category == "dependency_risk"]
        assert len(deps) == 1
        assert "Database" in deps[0].title
        assert deps[0].severity == "medium"

    def test_dependency_multiple_high_severity(self):
        e_db = Entity(entity_id="e-db", name="DB", entity_type="system", confidence="medium")
        apps = [
            Entity(entity_id=f"e-app{i}", name=f"App{i}", entity_type="system", confidence="medium")
            for i in range(1, 5)
        ]
        rels = [
            Relationship(
                relationship_id=f"r{i}",
                source_entity_id=app.entity_id,
                relation_type="depends_on",
                target_entity_id=e_db.entity_id,
                confidence="medium",
            )
            for i, app in enumerate(apps, start=1)
        ]
        store = run_detectors(graph=self._make_graph([e_db] + apps, rels))
        deps = [i for i in store.insights if i.category == "dependency_risk"]
        assert len(deps) == 1
        assert deps[0].severity == "high"

    def test_contradiction_detector(self):
        e_src = Entity(entity_id="e-src", name="Plan A", entity_type="decision", confidence="medium")
        e_tgt = Entity(entity_id="e-tgt", name="Plan B", entity_type="decision", confidence="medium")
        rel = Relationship(
            relationship_id="r-con",
            source_entity_id=e_src.entity_id,
            relation_type="contradicts",
            target_entity_id=e_tgt.entity_id,
            confidence="medium",
        )
        store = run_detectors(graph=self._make_graph([e_src, e_tgt], [rel]))
        contras = [i for i in store.insights if i.category == "contradiction"]
        assert len(contras) == 1
        assert contras[0].severity == "high"
        assert "Plan A" in contras[0].title
        assert "Plan B" in contras[0].title

    def test_ownership_gap_system_without_owner(self):
        e_sys = Entity(entity_id="e-sys", name="LegacyAuth", entity_type="system", confidence="medium")
        e_app = Entity(entity_id="e-app", name="App", entity_type="system", confidence="medium")
        rels = [
            Relationship(
                relationship_id="r1",
                source_entity_id=e_app.entity_id,
                relation_type="depends_on",
                target_entity_id=e_sys.entity_id,
                confidence="medium",
            ),
        ]
        store = run_detectors(graph=self._make_graph([e_sys, e_app], rels))
        gaps = [i for i in store.insights if i.category in ("strategic_gap", "operations_bottleneck")]
        system_gaps = [g for g in gaps if "LegacyAuth" in g.title]
        assert len(system_gaps) >= 1


# ---------------------------------------------------------------------------
# CLI tests
# ---------------------------------------------------------------------------


class TestDetectPatternsCLI:
    def test_command_exits_0_gracefully(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = CliRunner().invoke(app, ["detect-patterns"])
        assert result.exit_code == 0

    def test_command_with_demo_data(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        CliRunner().invoke(app, ["init-data-catalog"])
        CliRunner().invoke(app, ["seed-demo-data"])
        CliRunner().invoke(app, ["profile-data"])

        result = CliRunner().invoke(app, ["detect-patterns"])
        assert result.exit_code == 0
        # Strip ANSI color codes for assertion
        output_no_ansi = result.output.replace("\x1b[1;36m", "").replace("\x1b[0m", "").replace("\x1b[1m", "")
        assert "Insights detected:" in output_no_ansi


class TestInspectInsightsCLI:
    def test_command_exits_0_no_insights(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = CliRunner().invoke(app, ["inspect-insights"])
        assert result.exit_code == 0

    def test_command_with_insights(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        CliRunner().invoke(app, ["init-data-catalog"])
        CliRunner().invoke(app, ["seed-demo-data"])
        CliRunner().invoke(app, ["profile-data"])

        docs_dir = tmp_path / "company_docs"
        docs_dir.mkdir(parents=True, exist_ok=True)
        (docs_dir / "systems.md").write_text(
            "Billing depends on LegacyAuth. LegacyAuth owned by Platform Team.",
            encoding="utf-8",
        )
        CliRunner().invoke(app, ["extract-graph"])
        CliRunner().invoke(app, ["detect-patterns"])

        result = CliRunner().invoke(app, ["inspect-insights"])
        assert result.exit_code == 0
        assert "Total insights:" in result.output


# ---------------------------------------------------------------------------
# Graceful handling tests
# ---------------------------------------------------------------------------


class TestGracefulHandling:
    def test_run_detectors_with_no_inputs(self):
        store = run_detectors()
        assert isinstance(store, InsightStore)
        assert store.insights == []

    def test_run_detectors_with_empty_graph(self):
        profiles = DataProfileStore()
        store = run_detectors(profiles=profiles, graph=KnowledgeGraph())
        assert store.insights == []

    def test_run_detectors_with_empty_profiles_graph_only(self):
        e1 = Entity(entity_id="e1", name="App1", entity_type="system", confidence="medium")
        e2 = Entity(entity_id="e2", name="App2", entity_type="system", confidence="medium")
        e3 = Entity(entity_id="e3", name="SharedDB", entity_type="system", confidence="medium")
        rels = [
            Relationship(
                relationship_id="r1",
                source_entity_id=e1.entity_id,
                relation_type="depends_on",
                target_entity_id=e3.entity_id,
                confidence="medium",
            ),
            Relationship(
                relationship_id="r2",
                source_entity_id=e2.entity_id,
                relation_type="depends_on",
                target_entity_id=e3.entity_id,
                confidence="medium",
            ),
        ]
        graph = KnowledgeGraph(entities=[e1, e2, e3], relationships=rels)
        store = run_detectors(profiles=DataProfileStore(), graph=graph)
        categories = {i.category for i in store.insights}
        assert "dependency_risk" in categories
