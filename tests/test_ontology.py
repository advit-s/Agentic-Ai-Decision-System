"""Tests for the v0.4 ontology layer."""

from __future__ import annotations

from pathlib import Path

import pytest

from decision_system.data_catalog.models import (
    ColumnProfile,
    DataCategory,
    DataProfileStore,
    DatasetProfile,
)
from decision_system.ontology.inspector import (
    inspect_ontology as _inspect_ontology_fn,
    render_ontology_inspection,
)
from decision_system.ontology.mapper import DEFAULT_CONCEPTS, map_profiles_to_ontology
from decision_system.ontology.models import ColumnMapping, OntologyConcept, OntologyMap
from decision_system.ontology.store import load_ontology, save_ontology
from typer.testing import CliRunner

from decision_system.cli import app


def _col(name: str) -> ColumnProfile:
    return ColumnProfile(
        name=name, dtype="str", missing_count=0,
        missing_pct=0.0, unique_count=5,
    )


def _profile_with(
    filename: str = "demo_financials.csv",
    category: DataCategory = "financial",
    row_count: int = 5,
    columns: list[ColumnProfile] | None = None,
    warnings: list[str] | None = None,
    dataset_id: str = "demo_financials",
) -> DatasetProfile:
    return DatasetProfile(
        dataset_id=dataset_id,
        category=category,
        filename=filename,
        row_count=row_count,
        column_count=len(columns or []),
        columns=columns or [],
        warnings=warnings or [],
    )


# ============================================================================
# Model tests
# ============================================================================


class TestOntologyConcept:
    def test_roundtrip(self):
        c = OntologyConcept(
            concept_id="revenue",
            name="Revenue",
            description="Gross revenue",
            concept_type="metric",
            aliases=["total_revenue"],
        )
        payload = c.model_dump(mode="json")
        assert OntologyConcept.model_validate(payload) == c

    def test_defaults(self):
        c = OntologyConcept(concept_id="x")
        assert c.name == ""
        assert c.concept_type == "unknown"
        assert c.aliases == []
        assert c.detector_hints == []


class TestColumnMapping:
    def test_roundtrip(self):
        m = ColumnMapping(
            dataset_id="d", source_filename="f.csv", category="financial",
            column_name="rev", mapped_concept_id="revenue",
        )
        payload = m.model_dump(mode="json")
        assert ColumnMapping.model_validate(payload) == m

    def test_defaults(self):
        m = ColumnMapping(
            dataset_id="d", source_filename="f.csv", category="financial",
            column_name="x", mapped_concept_id="y",
        )
        assert m.mapped_concept_name == ""
        assert m.confidence == "high"
        assert m.reason == ""


class TestOntologyMap:
    def test_roundtrip(self):
        om = OntologyMap(
            concepts=[OntologyConcept(concept_id="revenue", name="Revenue")],
            column_mappings=[
                ColumnMapping(
                    dataset_id="d", source_filename="f.csv", category="financial",
                    column_name="rev", mapped_concept_id="revenue",
                )
            ],
        )
        payload = om.model_dump(mode="json")
        restored = OntologyMap.model_validate(payload)
        assert len(restored.concepts) == 1
        assert len(restored.column_mappings) == 1

    def test_empty(self):
        om = OntologyMap()
        assert om.concepts == []
        assert om.column_mappings == []

    def test_concept_by_id(self):
        om = OntologyMap(concepts=[
            OntologyConcept(concept_id="revenue", name="Revenue"),
            OntologyConcept(concept_id="expense", name="Expense"),
        ])
        assert om.concept_by_id("revenue").name == "Revenue"
        assert om.concept_by_id("nonexistent") is None

    def test_mappings_for_dataset(self):
        om = OntologyMap(column_mappings=[
            ColumnMapping(dataset_id="ds1", source_filename="f.csv", category="financial", column_name="rev", mapped_concept_id="revenue"),
            ColumnMapping(dataset_id="ds2", source_filename="g.csv", category="marketing", column_name="spend", mapped_concept_id="marketing_spend"),
        ])
        assert len(om.mappings_for_dataset("ds1")) == 1
        assert om.mappings_for_dataset("ds1")[0].mapped_concept_id == "revenue"
        assert len(om.mappings_for_dataset("ds2")) == 1

    def test_mappings_for_concept(self):
        om = OntologyMap(column_mappings=[
            ColumnMapping(dataset_id="ds1", source_filename="f.csv", category="financial", column_name="rev", mapped_concept_id="revenue"),
            ColumnMapping(dataset_id="ds2", source_filename="g.csv", category="sales", column_name="total", mapped_concept_id="revenue"),
        ])
        mappings = om.mappings_for_concept("revenue")
        assert len(mappings) == 2


# ============================================================================
# Default concepts tests
# ============================================================================


class TestDefaultConcepts:
    def test_count(self):
        assert len(DEFAULT_CONCEPTS) == 38

    def test_new_concepts_present(self):
        ids = {c.concept_id for c in DEFAULT_CONCEPTS}
        new_concepts = [
            "time_period", "page", "session_count",
            "traffic_source", "competitor", "process", "return_rate",
        ]
        for c in new_concepts:
            assert c in ids, f"Missing new concept: {c}"

    def test_unique_ids(self):
        ids = [c.concept_id for c in DEFAULT_CONCEPTS]
        assert len(ids) == len(set(ids))

    def test_required_present(self):
        ids = {c.concept_id for c in DEFAULT_CONCEPTS}
        required = [
            "revenue", "expense", "profit_margin", "product", "customer",
            "customer_segment", "customer_lifetime_value", "city", "region",
            "sales_amount", "lead_source", "marketing_channel", "marketing_spend",
            "click_count", "conversion_count", "conversion_rate", "bounce_rate",
            "refund_requested", "sentiment", "complaint_issue", "competitor_price",
            "our_price", "review_score", "operational_delay", "bottleneck",
            "strategic_goal", "constraint", "owner", "dependency", "contradiction",
            "risk",
        ]
        for r in required:
            assert r in ids, f"Missing concept: {r}"


# ============================================================================
# Mapper tests
# ============================================================================


class TestOntologyMapper:
    def test_maps_revenue(self):
        profile = _profile_with(
            filename="demo_financials.csv",
            category="financial",
            columns=[_col("revenue")],
        )
        om = map_profiles_to_ontology(DataProfileStore(profiles=[profile]))
        assert len(om.column_mappings) == 1
        assert om.column_mappings[0].mapped_concept_id == "revenue"
        assert om.column_mappings[0].confidence == "high"

    def test_maps_expenses(self):
        profile = _profile_with(
            filename="demo_financials.csv",
            category="financial",
            columns=[_col("expenses"), _col("cost")],
        )
        concept_ids = {m.mapped_concept_id for m in map_profiles_to_ontology(DataProfileStore(profiles=[profile])).column_mappings}
        assert "expense" in concept_ids

    def test_maps_profit_margin(self):
        profile = _profile_with(
            filename="demo_financials.csv",
            category="financial",
            columns=[_col("profit_margin")],
        )
        om = map_profiles_to_ontology(DataProfileStore(profiles=[profile]))
        assert om.column_mappings[0].mapped_concept_id == "profit_margin"

    def test_maps_lead_source(self):
        profile = _profile_with(
            filename="demo_sales.csv",
            category="sales",
            columns=[_col("lead_source")],
        )
        om = map_profiles_to_ontology(DataProfileStore(profiles=[profile]))
        assert om.column_mappings[0].mapped_concept_id == "lead_source"

    def test_maps_channel_to_marketing_channel(self):
        profile = _profile_with(
            filename="demo_marketing.csv",
            category="marketing",
            columns=[_col("channel")],
        )
        om = map_profiles_to_ontology(DataProfileStore(profiles=[profile]))
        assert om.column_mappings[0].mapped_concept_id == "marketing_channel"

    def test_maps_refund_requested(self):
        profile = _profile_with(
            filename="demo_feedback.csv",
            category="feedback",
            columns=[_col("refund_requested")],
        )
        om = map_profiles_to_ontology(DataProfileStore(profiles=[profile]))
        assert om.column_mappings[0].mapped_concept_id == "refund_requested"

    def test_maps_sentiment(self):
        profile = _profile_with(
            filename="demo_feedback.csv",
            category="feedback",
            columns=[_col("sentiment")],
        )
        om = map_profiles_to_ontology(DataProfileStore(profiles=[profile]))
        assert om.column_mappings[0].mapped_concept_id == "sentiment"

    def test_maps_issue_type(self):
        profile = _profile_with(
            filename="demo_feedback.csv",
            category="feedback",
            columns=[_col("issue_type")],
        )
        om = map_profiles_to_ontology(DataProfileStore(profiles=[profile]))
        assert om.column_mappings[0].mapped_concept_id == "complaint_issue"

    def test_unmapped_skipped(self):
        profile = _profile_with(
            filename="demo_unknown.csv",
            category="unknown",
            columns=[_col("xyz_unknown_col")],
        )
        om = map_profiles_to_ontology(DataProfileStore(profiles=[profile]))
        assert om.column_mappings == []

    def test_case_insensitive(self):
        profile = _profile_with(
            filename="test.csv",
            category="financial",
            columns=[_col("REVENUE"), _col("Revenue"), _col("revenue")],
        )
        om = map_profiles_to_ontology(DataProfileStore(profiles=[profile]))
        assert len(om.column_mappings) == 3

    def test_multiple_datasets(self):
        p1 = _profile_with(
            dataset_id="fin", filename="fin.csv", category="financial",
            columns=[_col("revenue")],
        )
        p2 = _profile_with(
            dataset_id="mkt", filename="mkt.csv", category="marketing",
            columns=[_col("spend")],
        )
        om = map_profiles_to_ontology(DataProfileStore(profiles=[p1, p2]))
        concept_ids = {m.mapped_concept_id for m in om.column_mappings}
        assert "revenue" in concept_ids
        assert "marketing_spend" in concept_ids  # spend in marketing -> marketing_spend

    def test_includes_default_concepts(self):
        profile = _profile_with(
            filename="d.csv", category="financial",
            columns=[_col("revenue")],
        )
        om = map_profiles_to_ontology(DataProfileStore(profiles=[profile]))
        assert len(om.concepts) == len(DEFAULT_CONCEPTS)
        ids = {c.concept_id for c in om.concepts}
        assert "revenue" in ids

    def test_maps_time_period_columns(self):
        profile = _profile_with(
            filename="d.csv", category="financial",
            columns=[_col("month"), _col("date"), _col("period"), _col("signup_month")],
        )
        om = map_profiles_to_ontology(DataProfileStore(profiles=[profile]))
        concept_ids = {m.mapped_concept_id for m in om.column_mappings}
        assert "time_period" in concept_ids

    def test_maps_page_column(self):
        profile = _profile_with(
            filename="d.csv", category="analytics",
            columns=[_col("page"), _col("page_path"), _col("url"), _col("landing_page")],
        )
        om = map_profiles_to_ontology(DataProfileStore(profiles=[profile]))
        concept_ids = {m.mapped_concept_id for m in om.column_mappings}
        assert "page" in concept_ids

    def test_maps_session_count_columns(self):
        profile = _profile_with(
            filename="d.csv", category="analytics",
            columns=[_col("sessions"), _col("page_sessions"), _col("visits")],
        )
        om = map_profiles_to_ontology(DataProfileStore(profiles=[profile]))
        concept_ids = {m.mapped_concept_id for m in om.column_mappings}
        assert "session_count" in concept_ids

    def test_maps_traffic_source_column(self):
        profile = _profile_with(
            filename="d.csv", category="analytics",
            columns=[_col("traffic_source"), _col("source"), _col("channel")],
        )
        om = map_profiles_to_ontology(DataProfileStore(profiles=[profile]))
        concept_ids = {m.mapped_concept_id for m in om.column_mappings}
        assert "traffic_source" in concept_ids

    def test_maps_competitor_column(self):
        profile = _profile_with(
            filename="d.csv", category="competitors",
            columns=[_col("competitor")],
        )
        om = map_profiles_to_ontology(DataProfileStore(profiles=[profile]))
        concept_ids = {m.mapped_concept_id for m in om.column_mappings}
        assert "competitor" in concept_ids

    def test_maps_process_column(self):
        profile = _profile_with(
            filename="d.csv", category="operations",
            columns=[_col("process"), _col("operation"), _col("process_name")],
        )
        om = map_profiles_to_ontology(DataProfileStore(profiles=[profile]))
        concept_ids = {m.mapped_concept_id for m in om.column_mappings}
        assert "process" in concept_ids

    def test_maps_return_rate_column(self):
        profile = _profile_with(
            filename="d.csv", category="products",
            columns=[_col("return_rate"), _col("returns"), _col("return_ratio")],
        )
        om = map_profiles_to_ontology(DataProfileStore(profiles=[profile]))
        concept_ids = {m.mapped_concept_id for m in om.column_mappings}
        assert "return_rate" in concept_ids


# ============================================================================
# Store tests
# ============================================================================


class TestOntologyStore:
    def test_save_and_load_roundtrip(self, tmp_path: Path):
        om = OntologyMap(
            concepts=[OntologyConcept(concept_id="revenue", name="Revenue")],
            column_mappings=[
                ColumnMapping(
                    dataset_id="d", source_filename="f.csv", category="financial",
                    column_name="rev", mapped_concept_id="revenue",
                )
            ],
        )
        saved = save_ontology(om, tmp_path / "onto_out")
        assert saved.exists()
        loaded = load_ontology(tmp_path / "onto_out")
        assert len(loaded.concepts) == 1
        assert len(loaded.column_mappings) == 1
        assert loaded.concepts[0].concept_id == "revenue"

    def test_load_missing_returns_empty(self, tmp_path: Path):
        om = load_ontology(tmp_path / "nonexistent")
        assert om.concepts == []
        assert om.column_mappings == []

    def test_save_creates_parent_dirs(self, tmp_path: Path):
        deep = tmp_path / "a" / "b" / "c"
        save_ontology(OntologyMap(), deep)
        assert (deep / "ontology_map.json").exists()


# ============================================================================
# Inspector tests
# ============================================================================


class TestOntologyInspector:
    def test_inspect_empty(self):
        summary = _inspect_ontology_fn(OntologyMap())
        assert summary["concept_count"] == 0
        assert summary["mapping_count"] == 0

    def test_inspect_with_data(self):
        om = OntologyMap(
            concepts=[
                OntologyConcept(concept_id="revenue", name="Revenue", concept_type="metric"),
                OntologyConcept(concept_id="expense", name="Expense", concept_type="metric"),
                OntologyConcept(concept_id="missing_data", name="Missing Data", concept_type="risk"),
            ],
            column_mappings=[
                ColumnMapping(dataset_id="d1", source_filename="f.csv", category="financial", column_name="revenue", mapped_concept_id="revenue"),
                ColumnMapping(dataset_id="d1", source_filename="f.csv", category="financial", column_name="cost", mapped_concept_id="expense"),
                ColumnMapping(dataset_id="d2", source_filename="g.csv", category="customers", column_name="email", mapped_concept_id="missing_data"),
            ],
        )
        summary = _inspect_ontology_fn(om)
        assert summary["concept_count"] == 3
        assert summary["mapping_count"] == 3
        assert summary["concept_type_counts"]["metric"] == 2
        assert summary["concept_type_counts"]["risk"] == 1

    def test_render_empty(self):
        output = render_ontology_inspection(_inspect_ontology_fn(OntologyMap()))
        # Empty map returns the "no map found" guidance message
        assert "no ontology map" in output.lower()

    def test_render_with_data(self):
        om = OntologyMap(
            concepts=[
                OntologyConcept(concept_id="revenue", name="Revenue", concept_type="metric"),
            ],
            column_mappings=[
                ColumnMapping(dataset_id="d1", source_filename="f.csv", category="financial", column_name="revenue", mapped_concept_id="revenue"),
            ],
        )
        output = render_ontology_inspection(_inspect_ontology_fn(om))
        assert "Concepts: 1" in output
        assert "revenue" in output


# ============================================================================
# CLI tests
# ============================================================================


class TestMapOntologyCLI:
    def test_with_demo_data(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        CliRunner().invoke(app, ["init-data-catalog"])
        CliRunner().invoke(app, ["seed-demo-data"])
        CliRunner().invoke(app, ["profile-data"])

        result = CliRunner().invoke(app, ["map-ontology"])
        assert result.exit_code == 0
        assert "concept" in result.output.lower() or "mapped" in result.output.lower()

    def test_exits_0_gracefully(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = CliRunner().invoke(app, ["map-ontology"])
        assert result.exit_code == 0


class TestInspectOntologyCLI:
    def test_exits_0_no_ontology(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = CliRunner().invoke(app, ["inspect-ontology"])
        assert result.exit_code == 0

    def test_with_ontology(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        CliRunner().invoke(app, ["init-data-catalog"])
        CliRunner().invoke(app, ["seed-demo-data"])
        CliRunner().invoke(app, ["profile-data"])
        CliRunner().invoke(app, ["map-ontology"])

        result = CliRunner().invoke(app, ["inspect-ontology"])
        assert result.exit_code == 0
        assert "concept" in result.output.lower()
