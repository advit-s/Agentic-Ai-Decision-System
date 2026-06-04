"""CLI entry points for the backend-first decision-system prototype.

The CLI indexes local documents and asks decision questions through the fixed
LangGraph workflow. The fake provider works without API keys; hosted providers
are optional and environment-configured.
"""

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

import typer
from pydantic import BaseModel
from rich.console import Console

from decision_system.config import load_settings
from decision_system.evals.runner import render_eval_report, run_eval_suite, save_eval_results
from decision_system.graph.workflow import build_workflow
from decision_system.rag.chunker import chunk_documents
from decision_system.rag.loader import load_documents
from decision_system.rag.vector_store import index_chunks, inspect_collection


app = typer.Typer(help="Create cited decision briefs from local company documents.")
console = Console()


def _to_jsonable(value: Any) -> Any:
    """Convert workflow state values into JSON-serializable data."""

    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_jsonable(item) for key, item in value.items()}
    return value


def _ask_json_payload(result: dict[str, Any]) -> dict[str, Any]:
    """Select the inspectable state required for `decision-system ask --json`."""

    return {
        "run_id": result.get("run_id"),
        "question": result.get("question"),
        "retrieved_evidence": _to_jsonable(result.get("retrieved_evidence", [])),
        "claims": _to_jsonable(result.get("claims", [])),
        "verification_results": _to_jsonable(result.get("verification_results", [])),
        "final_report": _to_jsonable(result.get("final_report")),
    }


def _render_evidence_section(evidence_items: list[Any]) -> str:
    """Render retrieved evidence as a compact Markdown audit section."""

    lines = ["# Retrieved Evidence", ""]
    if not evidence_items:
        lines.append("(none)")
        return "\n".join(lines)

    for index, evidence in enumerate(evidence_items, start=1):
        preview = " ".join(evidence.text.split())
        if len(preview) > 240:
            preview = f"{preview[:237]}..."
        score = "" if evidence.score is None else f"{evidence.score:.6f}"
        lines.extend(
            [
                f"## Evidence {index}",
                f"- evidence_id: {evidence.evidence_id}",
                f"- source_filename: {evidence.source_filename}",
                f"- chunk_id: {evidence.chunk_id}",
                f"- score: {score}",
                f"- text preview: {preview}",
                "",
            ]
        )
    return "\n".join(lines).rstrip()


def _save_run(result: dict[str, Any]) -> Path:
    """Persist the full workflow result under `.decision_system/runs/`."""

    runs_dir = Path(".decision_system") / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    run_path = runs_dir / f"{result['run_id']}.json"
    run_path.write_text(
        json.dumps(_to_jsonable(result), indent=2) + "\n",
        encoding="utf-8",
    )
    return run_path.resolve()


@app.command()
def index() -> None:
    """Index local documents from the configured docs directory.

    Inputs come from environment-backed settings. The command reads `.md` and
    `.txt` files, chunks them, and writes a local Chroma collection. Its main
    side effect is refreshing the configured vector store.
    """

    settings = load_settings()
    documents = load_documents(settings.docs_dir)
    chunks = chunk_documents(documents)
    chunk_count = index_chunks(
        chunks,
        store_dir=settings.store_dir,
        collection_name=settings.collection_name,
    )
    console.print(f"Indexed {len(documents)} documents into {chunk_count} chunks.")


@app.command()
def inspect_index() -> None:
    """Inspect the configured local Chroma collection."""

    settings = load_settings()
    inspection = inspect_collection(
        store_dir=settings.store_dir,
        collection_name=settings.collection_name,
    )
    source_filenames = ", ".join(inspection.source_filenames) or "(none)"
    console.print(f"Collection name: {inspection.collection_name}")
    console.print(f"Chunk count: {inspection.chunk_count}")
    console.print(f"Unique source filenames: {source_filenames}")


@app.command()
def ask(
    question: str,
    top_k: int = typer.Option(6, "--top-k", help="Maximum evidence chunks to retrieve."),
    show_evidence: bool = typer.Option(
        False,
        "--show-evidence",
        help="Print retrieved evidence before the Markdown report.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Print structured JSON instead of Markdown.",
    ),
    save_run: bool = typer.Option(
        False,
        "--save-run",
        help="Save the full workflow result to .decision_system/runs/.",
    ),
    provider: str | None = typer.Option(
        None,
        "--provider",
        help="Provider for this run: fake or nvidia_nim.",
    ),
) -> None:
    """Run the decision workflow for a CLI question.

    Args:
        question: Decision question to analyze.
        top_k: Maximum evidence chunks to retrieve.

    The command prints Markdown to stdout. It uses the fake provider by default
    and does not execute external actions in v0.1.
    """

    graph = build_workflow()
    graph_input: dict[str, Any] = {
        "run_id": str(uuid4()),
        "question": question,
        "top_k": top_k,
    }
    if provider is not None:
        graph_input["provider"] = provider
    result = graph.invoke(graph_input)
    saved_path = _save_run(result) if save_run else None

    if json_output:
        payload = _ask_json_payload(result)
        if saved_path is not None:
            payload["saved_run_path"] = str(saved_path)
        typer.echo(json.dumps(payload, indent=2))
        return

    if show_evidence:
        typer.echo(_render_evidence_section(result.get("retrieved_evidence", [])))
        typer.echo()
    typer.echo(result["final_report"].markdown)
    if saved_path is not None:
        typer.echo(f"Saved run: {saved_path}")


@app.command("eval")
def evaluate(
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Print structured evaluation JSON instead of text.",
    ),
    save_results: bool = typer.Option(
        False,
        "--save-results",
        help="Save evaluation results under evals/results/.",
    ),
) -> None:
    """Run the local offline evaluation suite."""

    suite_result = run_eval_suite()
    if save_results:
        suite_result = save_eval_results(suite_result)

    if json_output:
        typer.echo(suite_result.model_dump_json(indent=2))
    else:
        typer.echo(render_eval_report(suite_result))

    if not suite_result.passed:
        raise typer.Exit(code=1)
