from typer.testing import CliRunner

from decision_system.cli import app


def test_cli_index_and_ask(tmp_path, monkeypatch):
    docs_dir = tmp_path / "company_docs"
    store_dir = tmp_path / "chroma"
    docs_dir.mkdir()
    (docs_dir / "billing.md").write_text(
        "Billing migration requires rollback planning.",
        encoding="utf-8",
    )
    monkeypatch.setenv("DECISION_DOCS_DIR", str(docs_dir))
    monkeypatch.setenv("DECISION_STORE_DIR", str(store_dir))
    monkeypatch.setenv("DECISION_COLLECTION", "test_cli_chunks")

    runner = CliRunner()
    index_result = runner.invoke(app, ["index"])
    ask_result = runner.invoke(app, ["ask", "Should we migrate billing?"])

    assert index_result.exit_code == 0
    assert "Indexed" in index_result.output
    assert ask_result.exit_code == 0
    assert "# Decision Report" in ask_result.output
