import json
from pathlib import Path

from typer.testing import CliRunner

from decision_system.cli import app
from decision_system.context.models import DecisionContext, InsightEvidence


def _configure_test_store(tmp_path, monkeypatch, collection_name="test_cli_chunks"):
    docs_dir = tmp_path / "company_docs"
    store_dir = tmp_path / "chroma"
    docs_dir.mkdir()
    (docs_dir / "billing.md").write_text(
        "Billing migration requires rollback planning.",
        encoding="utf-8",
    )
    monkeypatch.setenv("DECISION_DOCS_DIR", str(docs_dir))
    monkeypatch.setenv("DECISION_STORE_DIR", str(store_dir))
    monkeypatch.setenv("DECISION_COLLECTION", collection_name)
    return docs_dir, store_dir


def test_cli_index_and_ask(tmp_path, monkeypatch):
    _configure_test_store(tmp_path, monkeypatch)
    runner = CliRunner()
    index_result = runner.invoke(app, ["index"])
    ask_result = runner.invoke(app, ["ask", "Should we migrate billing?"])

    assert index_result.exit_code == 0
    assert "Indexed" in index_result.output
    assert ask_result.exit_code == 0
    assert "# Decision Report" in ask_result.output


def test_inspect_index_empty_store(tmp_path, monkeypatch):
    _configure_test_store(tmp_path, monkeypatch, collection_name="empty_chunks")

    result = CliRunner().invoke(app, ["inspect-index"])

    assert result.exit_code == 0
    assert "Collection name: empty_chunks" in result.output
    # Rich outputs ANSI color codes, strip them for assertion
    output_no_ansi = result.output.replace("\x1b[1;36m", "").replace("\x1b[0m", "").replace("\x1b[1m", "")
    assert "Chunk count: 0" in output_no_ansi
    assert "Unique source filenames: (none)" in output_no_ansi


def test_inspect_index_after_indexing(tmp_path, monkeypatch):
    _configure_test_store(tmp_path, monkeypatch, collection_name="indexed_chunks")
    runner = CliRunner()

    index_result = runner.invoke(app, ["index"])
    inspect_result = runner.invoke(app, ["inspect-index"])

    assert index_result.exit_code == 0
    assert inspect_result.exit_code == 0
    assert "Collection name: indexed_chunks" in inspect_result.output
    # Rich outputs ANSI color codes, strip them for assertion
    output_no_ansi = inspect_result.output.replace("\x1b[1;36m", "").replace("\x1b[0m", "").replace("\x1b[1m", "")
    assert "Chunk count: 1" in output_no_ansi
    assert "billing.md" in inspect_result.output


def test_ask_show_evidence(tmp_path, monkeypatch):
    _configure_test_store(tmp_path, monkeypatch)
    runner = CliRunner()
    runner.invoke(app, ["index"])

    result = runner.invoke(
        app,
        ["ask", "Should we migrate billing?", "--show-evidence"],
    )

    assert result.exit_code == 0
    assert "# Retrieved Evidence" in result.output
    assert "## Evidence 1" in result.output
    assert "- evidence_id:" in result.output
    assert "- source_filename: billing.md" in result.output
    assert "- chunk_id: chunk-0001" in result.output
    assert "- score:" in result.output
    assert "- text preview: Billing migration requires rollback planning." in result.output
    assert result.output.index("# Retrieved Evidence") < result.output.index("# Decision Report")


def test_ask_json_outputs_structured_state(tmp_path, monkeypatch):
    _configure_test_store(tmp_path, monkeypatch)
    runner = CliRunner()
    runner.invoke(app, ["index"])

    result = runner.invoke(app, ["ask", "Should we migrate billing?", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["run_id"]
    assert payload["question"] == "Should we migrate billing?"
    assert payload["retrieved_evidence"][0]["source_filename"] == "billing.md"
    assert payload["claims"]
    assert payload["verification_results"]
    assert payload["final_report"]["markdown"].startswith("# Decision Report")


def test_ask_save_run_writes_json_file(tmp_path, monkeypatch):
    _configure_test_store(tmp_path, monkeypatch)
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    runner.invoke(app, ["index"])

    result = runner.invoke(app, ["ask", "Should we migrate billing?", "--save-run"])

    assert result.exit_code == 0
    saved_line = next(line for line in result.output.splitlines() if line.startswith("Saved run: "))
    saved_path = Path(saved_line.removeprefix("Saved run: "))
    assert saved_path.exists()
    payload = json.loads(saved_path.read_text(encoding="utf-8"))
    assert payload["run_id"]
    assert payload["question"] == "Should we migrate billing?"
    assert payload["retrieved_evidence"][0]["source_filename"] == "billing.md"
    assert payload["claims"]
    assert payload["verification_results"]
    assert payload["final_report"]["markdown"].startswith("# Decision Report")


def test_ask_provider_fake_keeps_offline_default(tmp_path, monkeypatch):
    _configure_test_store(tmp_path, monkeypatch)
    runner = CliRunner()
    runner.invoke(app, ["index"])

    result = runner.invoke(
        app,
        ["ask", "Should we migrate billing?", "--provider", "fake"],
    )

    assert result.exit_code == 0
    assert "# Decision Report" in result.output


class _FakeDecisionContextBuilder:
    def build(self, question, run_id=None, **_kwargs):
        return DecisionContext(
            run_id=run_id or "context-run-1",
            question=question,
            relevant_ontology_concepts=[
                {
                    "concept_id": "revenue",
                    "name": "Revenue",
                    "type": "metric",
                    "required": True,
                }
            ],
            relevant_insights=[
                InsightEvidence(
                    insight_id="insight-1",
                    title="Detected revenue pressure",
                    category="revenue_risk",
                    severity="high",
                    confidence="high",
                    evidence_summary="Synthetic revenue signal found in local profiles.",
                    recommended_action="Review cost and revenue drivers with a human owner.",
                    ontology_concepts=["revenue"],
                    source_ids=["demo_financial"],
                )
            ],
            graph_signals=["Billing depends on LegacyAuth"],
            orchestration_summary={
                "run_id": "orch-1",
                "decision_type": "financial",
                "insight_count": 1,
                "insights_by_severity": {"high": 1},
            },
            judge_summary={
                "confidence_level": "low",
                "key_findings": ["Human review is needed."],
                "human_review_required": ["Validate high-severity signal."],
            },
            human_review_items=["High-severity insight: Detected revenue pressure"],
        )


def test_ask_include_insights_adds_insight_sections_only(tmp_path, monkeypatch):
    _configure_test_store(tmp_path, monkeypatch)
    monkeypatch.setattr("decision_system.cli.DecisionContextBuilder", _FakeDecisionContextBuilder)
    runner = CliRunner()
    runner.invoke(app, ["index"])

    result = runner.invoke(app, ["ask", "Where are we losing money?", "--include-insights"])

    assert result.exit_code == 0
    assert "## Business/Data Insights" in result.output
    assert "Detected revenue pressure" in result.output
    assert "## Ontology Concepts Used" in result.output
    assert "## Graph and Relationship Signals" in result.output
    assert "## Orchestration Summary" not in result.output
    assert "Judge flag:" not in result.output


def test_ask_orchestrated_adds_orchestration_without_insight_cards(tmp_path, monkeypatch):
    _configure_test_store(tmp_path, monkeypatch)
    monkeypatch.setattr("decision_system.cli.DecisionContextBuilder", _FakeDecisionContextBuilder)
    runner = CliRunner()
    runner.invoke(app, ["index"])

    result = runner.invoke(app, ["ask", "Where are we losing money?", "--orchestrated"])

    assert result.exit_code == 0
    assert "## Orchestration Summary" in result.output
    assert "### Judge Summary" in result.output
    assert "## Business/Data Insights" not in result.output


def test_ask_save_context_writes_json_without_report_sections(tmp_path, monkeypatch):
    _configure_test_store(tmp_path, monkeypatch)
    saved_paths: list[Path] = []

    def _fake_save_context(context):
        path = tmp_path / ".decision_system" / "contexts" / f"{context.run_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(context.model_dump_json(indent=2), encoding="utf-8")
        saved_paths.append(path)
        return path

    monkeypatch.setattr("decision_system.cli.DecisionContextBuilder", _FakeDecisionContextBuilder)
    monkeypatch.setattr("decision_system.cli.save_decision_context", _fake_save_context)
    runner = CliRunner()
    runner.invoke(app, ["index"])

    result = runner.invoke(app, ["ask", "Where are we losing money?", "--save-context"])

    assert result.exit_code == 0
    assert "Saved context:" in result.output
    assert saved_paths
    payload = json.loads(saved_paths[0].read_text(encoding="utf-8"))
    assert payload["run_id"]
    assert payload["question"] == "Where are we losing money?"
    assert payload["relevant_insights"][0]["insight_id"] == "insight-1"
    assert "## Business/Data Insights" not in result.output
    assert "## Orchestration Summary" not in result.output


def test_ask_json_save_context_outputs_valid_json(tmp_path, monkeypatch):
    _configure_test_store(tmp_path, monkeypatch)
    saved_paths: list[Path] = []

    def _fake_save_context(context):
        path = tmp_path / ".decision_system" / "contexts" / f"{context.run_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(context.model_dump_json(indent=2), encoding="utf-8")
        saved_paths.append(path)
        return path

    monkeypatch.setattr("decision_system.cli.DecisionContextBuilder", _FakeDecisionContextBuilder)
    monkeypatch.setattr("decision_system.cli.save_decision_context", _fake_save_context)
    runner = CliRunner()
    runner.invoke(app, ["index"])

    result = runner.invoke(
        app,
        ["ask", "Where are we losing money?", "--json", "--save-context"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["saved_context_path"] == str(saved_paths[0])
    assert payload["decision_context"]["relevant_insights"][0]["insight_id"] == "insight-1"


def test_build_context_json_outputs_structured_context(monkeypatch):
    monkeypatch.setattr("decision_system.cli.DecisionContextBuilder", _FakeDecisionContextBuilder)

    result = CliRunner().invoke(app, ["build-context", "Where are we losing money?", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["question"] == "Where are we losing money?"
    assert payload["relevant_insights"][0]["insight_id"] == "insight-1"
    assert payload["relevant_ontology_concepts"][0]["concept_id"] == "revenue"


def test_build_context_json_save_outputs_valid_json(tmp_path, monkeypatch):
    saved_paths: list[Path] = []

    def _fake_save_context(context):
        path = tmp_path / ".decision_system" / "contexts" / f"{context.run_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(context.model_dump_json(indent=2), encoding="utf-8")
        saved_paths.append(path)
        return path

    monkeypatch.setattr("decision_system.cli.DecisionContextBuilder", _FakeDecisionContextBuilder)
    monkeypatch.setattr("decision_system.cli.save_decision_context", _fake_save_context)

    result = CliRunner().invoke(
        app,
        ["build-context", "Where are we losing money?", "--json", "--save"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["saved_context_path"] == str(saved_paths[0])
    assert payload["relevant_insights"][0]["insight_id"] == "insight-1"


def test_build_context_save_writes_context(tmp_path, monkeypatch):
    saved_paths: list[Path] = []

    def _fake_save_context(context):
        path = tmp_path / ".decision_system" / "contexts" / f"{context.run_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(context.model_dump_json(indent=2), encoding="utf-8")
        saved_paths.append(path)
        return path

    monkeypatch.setattr("decision_system.cli.DecisionContextBuilder", _FakeDecisionContextBuilder)
    monkeypatch.setattr("decision_system.cli.save_decision_context", _fake_save_context)

    result = CliRunner().invoke(app, ["build-context", "Where are we losing money?", "--save"])

    assert result.exit_code == 0
    assert "Saved context:" in result.output
    assert saved_paths[0].exists()


def test_extract_graph_exits_0(tmp_path, monkeypatch):
    docs_dir, _ = _configure_test_store(tmp_path, monkeypatch)
    (docs_dir / "systems.md").write_text(
        "Billing depends on LegacyAuth. LegacyAuth owned by Platform Team.",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(app, ["extract-graph"])

    assert result.exit_code == 0
    assert "Saved knowledge graph:" in result.output
    graph_path = tmp_path / ".decision_system" / "graph" / "knowledge_graph.json"
    assert graph_path.exists()
    payload = json.loads(graph_path.read_text(encoding="utf-8"))
    assert payload["entities"]
    assert payload["relationships"]


def test_inspect_graph_exits_0(tmp_path, monkeypatch):
    docs_dir, _ = _configure_test_store(tmp_path, monkeypatch)
    (docs_dir / "systems.md").write_text(
        "Billing depends on LegacyAuth. LegacyAuth owned by Platform Team.",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    extract_result = runner.invoke(app, ["extract-graph"])

    result = runner.invoke(app, ["inspect-graph"])

    assert extract_result.exit_code == 0
    assert result.exit_code == 0
    assert "Total entity count:" in result.output
    assert "Total relationship count:" in result.output
    assert "Entities grouped by type:" in result.output
    assert "Relationships grouped by relation type:" in result.output
    assert "Top connected entities:" in result.output
