import json
from pathlib import Path

from typer.testing import CliRunner

from decision_system.cli import app


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
    assert "Chunk count: 0" in result.output
    assert "Unique source filenames: (none)" in result.output


def test_inspect_index_after_indexing(tmp_path, monkeypatch):
    _configure_test_store(tmp_path, monkeypatch, collection_name="indexed_chunks")
    runner = CliRunner()

    index_result = runner.invoke(app, ["index"])
    inspect_result = runner.invoke(app, ["inspect-index"])

    assert index_result.exit_code == 0
    assert inspect_result.exit_code == 0
    assert "Collection name: indexed_chunks" in inspect_result.output
    assert "Chunk count: 1" in inspect_result.output
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
