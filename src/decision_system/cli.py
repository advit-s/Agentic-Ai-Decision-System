"""CLI entry points for the backend-first decision-system prototype.

The CLI indexes local documents and asks decision questions through the fixed
LangGraph workflow. The fake provider works without API keys; hosted providers
are optional and environment-configured.

Subpackage imports are lazy -- loaded inside the heavy command functions -- so
that lightweight introspection commands (``--help``, ``check-hygiene``) avoid
pulling in LangGraph, Chroma, RAG, agent nodes, eval runners, or war-room
modules at import time.

Only the few symbols that tests regularly monkeypatch via
``monkeypatch.setattr("decision_system.cli.<name>")`` (``DecisionContextBuilder``,
``save_decision_context``, and ``render_decision_report``) plus the web UI
static assets remain at module scope.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

import typer
from pydantic import BaseModel
from rich.console import Console

# Heavy third-party imports (chromadb, LangGraph, etc.) are intentionally
# deferred into command functions so that lightweight commands (``--help``,
# ``check-hygiene``) remain fast.  A string-based helper below detects
# missing-index errors without importing chromadb at module scope.

# ---------------------------------------------------------------------------
# Lightweight imports: config, hygiene, hygiene HTML renderer, data catalog
# store/inspector, and the three symbols tests monkeypatch by dotted path.
# ---------------------------------------------------------------------------
from decision_system.config import load_settings  # noqa: E402
from decision_system.devtools.hygiene import (  # noqa: E402
    HygieneReport,
    check_hygiene as _run_hygiene_fn,
)
from decision_system.data_catalog.demo_data import (  # noqa: E402
    seed_demo_data as _seed_demo_data_fn,
)
from decision_system.data_catalog.importer import (  # noqa: E402
    DEFAULT_IMPORT_SOURCE_DIR,
    import_datasets as import_datasets_fn,
    load_import_manifest,
    render_import_manifest,
)
from decision_system.data_catalog.initializer import (  # noqa: E402
    DEFAULT_DATA_ROOT,
    init_data_catalog as initialize_data_catalog,
)
from decision_system.data_catalog.inspector import (  # noqa: E402
    inspect_profiles,
    render_inspection,
)
from decision_system.data_catalog.store import (  # noqa: E402
    load_profiles,
    profile_and_save,
    save_profiles,
)
from decision_system.context.builder import (  # noqa: E402  # monkeypatched by tests
    DecisionContextBuilder,
)
from decision_system.context.inspector import (  # noqa: E402
    inspect_context,
    render_context_inspection,
)
from decision_system.context.models import DecisionContext  # noqa: E402
from decision_system.context.store import (  # noqa: E402
    save_context as save_decision_context,  # monkeypatched by tests
)

app = typer.Typer(help="Create cited decision briefs from local company documents.")

# ---------------------------------------------------------------------------
# Optional workspace sub-commands (v1.0) -- self-contained sub-module.
# ---------------------------------------------------------------------------
try:
    from decision_system.cli_workspaces import register_workspace_commands  # noqa: E402
    register_workspace_commands(app)
except ImportError:
    pass

# ---------------------------------------------------------------------------
# Optional connector sub-commands (v1.1) -- self-contained sub-module.
# ---------------------------------------------------------------------------
try:
    from decision_system.cli_connectors import (  # noqa: E402
        register_connector_commands,
    )
    register_connector_commands(app)
except ImportError:
    pass

console = Console()


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _is_missing_index_error(exc: Exception) -> bool:
    """Return True when *exc* signals a missing Chroma collection.

    Avoids importing ``chromadb`` at function-definition time so that the
    helper itself does not pull heavy dependencies.  Detection is done via
    class-name and message inspection.
    """
    name = exc.__class__.__name__
    module = exc.__class__.__module__ or ""
    message = str(exc)
    return (
        name == "NotFoundError" and "chromadb" in module
    ) or "Collection [decision_chunks] does not exist" in message


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
    """Select the inspectable state required for ``decision-system ask --json``."""
    return {
        "run_id": result.get("run_id"),
        "question": result.get("question"),
        "retrieved_evidence": _to_jsonable(result.get("retrieved_evidence", [])),
        "claims": _to_jsonable(result.get("claims", [])),
        "verification_results": _to_jsonable(
            result.get("verification_results", [])
        ),
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
                "",
                f"- text preview: {preview}",
                "",
            ]
        )
    return "\n".join(lines).rstrip()


def _save_run(result: dict[str, Any]) -> Path:
    """Persist the full workflow result under ``.decision_system/runs/``."""
    runs_dir = Path(".decision_system") / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    run_path = runs_dir / f"{result['run_id']}.json"
    run_path.write_text(
        json.dumps(_to_jsonable(result), indent=2) + "\n",
        encoding="utf-8",
    )
    return run_path.resolve()


# ---------------------------------------------------------------------------
# Commands -- heavy imports are deferred into each function body.
# ---------------------------------------------------------------------------


@app.command()
def index() -> None:
    """Index local documents from the configured docs directory."""
    # Defer graph/workflow (LangGraph) import; only the document pipeline is needed here.
    from decision_system.graph.workflow import build_workflow  # noqa: PLC0415
    from decision_system.rag.chunker import chunk_documents  # noqa: PLC0415
    from decision_system.rag.loader import load_documents  # noqa: PLC0415
    from decision_system.rag.vector_store import index_chunks  # noqa: PLC0415

    settings = load_settings()
    documents = load_documents(settings.docs_dir)
    chunks = chunk_documents(documents)
    chunk_count = index_chunks(
        chunks,
        store_dir=settings.store_dir,
        collection_name=settings.collection_name,
    )
    console.print(
        f"Indexed {len(documents)} documents into {chunk_count} chunks."
    )


@app.command()
def inspect_index() -> None:
    """Inspect the configured local Chroma collection."""
    from decision_system.rag.vector_store import inspect_collection  # noqa: PLC0415

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
def extract_graph() -> None:
    """Extract a local knowledge graph from configured company documents."""
    from decision_system.graphing.extractor import (  # noqa: PLC0415
        extract_knowledge_graph,
    )
    from decision_system.graphing.store import (  # noqa: PLC0415
        save_knowledge_graph,
    )
    from decision_system.rag.chunker import chunk_documents  # noqa: PLC0415
    from decision_system.rag.loader import load_documents  # noqa: PLC0415

    settings = load_settings()
    documents = load_documents(settings.docs_dir)
    chunks = chunk_documents(documents)
    knowledge_graph = extract_knowledge_graph(chunks)
    graph_path = save_knowledge_graph(knowledge_graph).resolve()
    console.print(f"Saved knowledge graph: {graph_path}")
    console.print(f"Entity count: {len(knowledge_graph.entities)}")
    console.print(
        f"Relationship count: {len(knowledge_graph.relationships)}"
    )


@app.command()
def inspect_graph() -> None:
    """Inspect the local graph-like JSON knowledge store."""
    from decision_system.graphing.inspector import (  # noqa: PLC0415
        inspect_knowledge_graph,
        render_graph_inspection,
    )
    from decision_system.graphing.store import (  # noqa: PLC0415
        load_knowledge_graph,
    )

    knowledge_graph = load_knowledge_graph()
    inspection = inspect_knowledge_graph(knowledge_graph)
    console.print(render_graph_inspection(inspection))


@app.command()
def detect_patterns() -> None:
    """Run deterministic pattern and vulnerability detection."""
    from decision_system.data_catalog.store import load_profiles  # noqa: PLC0415
    from decision_system.graphing.store import load_knowledge_graph  # noqa: PLC0415
    from decision_system.insights.detectors import run_detectors  # noqa: PLC0415
    from decision_system.insights.store import save_insights  # noqa: PLC0415

    profiles = load_profiles(
        ".decision_system/data_profiles/profiles.json"
    )
    graph = load_knowledge_graph()
    store = run_detectors(profiles=profiles, graph=graph)
    insights_path = save_insights(store)
    severity_counts = store.severity_counts()
    category_counts = store.category_counts()
    console.print(f"Insights detected: {len(store.insights)}")
    if severity_counts:
        console.print(
            "By severity: "
            + ", ".join(
                f"{k}: {v}" for k, v in sorted(severity_counts.items())
            )
        )
    if category_counts:
        console.print(
            "By category: "
            + ", ".join(
                f"{k}: {v}" for k, v in sorted(category_counts.items())
            )
        )
    console.print(f"Saved insights: {insights_path}")


@app.command()
def inspect_insights() -> None:
    """Inspect saved deterministic insight summaries."""
    from decision_system.insights.inspector import (  # noqa: PLC0415
        inspect_insights as _inspect_insights_fn,
        render_insight_inspection,
    )
    from decision_system.insights.store import load_insights  # noqa: PLC0415

    store = load_insights()
    summary = _inspect_insights_fn(store)
    console.print(render_insight_inspection(summary))


@app.command()
def analyze_problem(
    question: str,
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Analyze a business question and print required data, tools, and roles."""
    from decision_system.orchestration.dispatcher import (  # noqa: PLC0415
        build_dispatch_plan,
    )
    from decision_system.orchestration.inspector import (  # noqa: PLC0415
        inspect_dispatch_plan,
        inspect_problem_analysis,
        render_dispatch_plan,
        render_problem_analysis,
    )
    from decision_system.orchestration.models import (  # noqa: PLC0415
        DispatchPlan,
        ProblemAnalysis,
    )
    from decision_system.orchestration.planner import (  # noqa: PLC0415
        plan_data_tools_roles,
    )
    from decision_system.orchestration.problem_analyzer import (  # noqa: PLC0415
        analyze_problem as _analyze_problem_fn,
    )

    analysis = _analyze_problem_fn(question)
    analysis = plan_data_tools_roles(analysis)
    summary = inspect_problem_analysis(analysis)
    if json_output:
        typer.echo(json.dumps(_to_jsonable(summary), indent=2))
    else:
        console.print(render_problem_analysis(summary))


@app.command()
def run_orchestration(
    question: str,
    json_output: bool = typer.Option(False, "--json"),
    save_run: bool = typer.Option(
        True,
        "--save-run/--no-save-run",
        help=(
            "Save the orchestration run under "
            ".decision_system/orchestration/runs/."
        ),
    ),
) -> None:
    """Run the full offline orchestration pipeline for a business question."""
    from decision_system.orchestration.judge import (  # noqa: PLC0415
        build_judge_summary,
    )
    from decision_system.orchestration.store import (  # noqa: PLC0415
        load_latest_session,
        save_decision_session,
    )
    from decision_system.orchestration.workflow import (  # noqa: PLC0415
        run_orchestration as _run_orchestration_fn,
    )

    result = _run_orchestration_fn(question, save=save_run)
    if json_output:
        typer.echo(json.dumps(_to_jsonable(result), indent=2))
        return
    console.print(f"Run ID: {result['run_id']}")
    console.print(f"Decision type: {result['decision_type']}")
    console.print(
        "Required data categories: "
        + ", ".join(result["required_data_categories"]) or "none"
    )
    console.print("Selected tools:")
    for tool in result["execution_order"]:
        console.print(f" - {tool}")
    console.print("Selected roles:")
    for role in result["relevant_roles"]:
        console.print(f" - {role}")
    console.print(f"Insights: {result['insight_count']}")
    console.print("Insights by severity:")
    for sev, count in sorted(result["insights_by_severity"].items()):
        console.print(f" - {sev}: {count}")
    j = result["judge"]
    console.print(f"Judge confidence: {j['confidence_level']}")
    console.print(
        f"Human review required: {len(j['human_review_required'])} items"
    )
    if result["saved_path"]:
        console.print(f"Saved run: {result['saved_path']}")


@app.command()
def inspect_orchestration() -> None:
    """Inspect the latest saved orchestration run."""
    from decision_system.orchestration.inspector import (  # noqa: PLC0415
        inspect_dispatch_plan,
        inspect_problem_analysis,
        render_dispatch_plan,
        render_problem_analysis,
    )
    from decision_system.orchestration.models import (  # noqa: PLC0415
        DispatchPlan,
        ProblemAnalysis,
    )
    from decision_system.orchestration.store import (  # noqa: PLC0415
        load_latest_session,
    )

    session = load_latest_session()
    if session is None:
        console.print(
            "No orchestration run found. "
            "Run `decision-system run-orchestration` first."
        )
        raise typer.Exit(code=0)

    analysis = ProblemAnalysis(
        question=session.question,
        decision_type=session.decision_type,
        required_data_categories=session.required_data_categories,
        required_tools=session.required_tools,
        relevant_roles=session.relevant_roles,
        required_storage_tiers=session.storage_tiers_used,
        analysis_notes=session.context_summary,
    )
    plan = DispatchPlan(
        selected_tools=session.required_tools,
        selected_roles=session.relevant_roles,
        selected_artifacts=session.selected_artifacts,
        execution_order=session.execution_order,
        skipped_tools=session.skipped_tools,
        missing_inputs=session.missing_inputs,
    )
    console.print(render_problem_analysis(inspect_problem_analysis(analysis)))
    console.print(render_dispatch_plan(inspect_dispatch_plan(plan)))
    console.print("# Judge Summary")
    console.print("")
    console.print(f"Run ID: {session.run_id}")
    console.print(f"Insight count: {session.insight_count}")
    console.print(f"Ontology concepts: {session.ontology_concept_count}")
    console.print(f"Mapped columns: {session.mapped_column_count}")
    judge = session.judge_summary
    if judge:
        console.print(f"Confidence: {judge.get('confidence_level', 'unknown')}")
        console.print(
            "Human review required: "
            f"{len(judge.get('human_review_required', []))} items"
        )


@app.command()
def map_ontology() -> None:
    """Map dataset columns to ontology business concepts."""
    from decision_system.data_catalog.store import (  # noqa: PLC0415
        load_profiles,
    )
    from decision_system.ontology.mapper import (  # noqa: PLC0415
        map_profiles_to_ontology,
    )
    from decision_system.ontology.store import (  # noqa: PLC0415
        DEFAULT_ONTOLOGY_DIR,
        save_ontology,
    )

    profiles = load_profiles()
    omap = map_profiles_to_ontology(profiles)
    ontology_path = save_ontology(omap)
    concept_count = len(omap.concepts)
    mapping_count = len(omap.column_mappings)
    console.print(
        f"Ontology mapped: {concept_count} concepts, "
        f"{mapping_count} column mappings"
    )
    console.print(f"Saved ontology map: {ontology_path}")


@app.command()
def inspect_ontology() -> None:
    """Inspect the local ontology map."""
    from decision_system.ontology.inspector import (  # noqa: PLC0415
        inspect_ontology as _inspect_ontology_fn,
        render_ontology_inspection,
    )
    from decision_system.ontology.store import load_ontology  # noqa: PLC0415

    omap = load_ontology()
    summary = _inspect_ontology_fn(omap)
    console.print(render_ontology_inspection(summary))


@app.command()
def init_data_catalog() -> None:
    """Create local company_data folders, manifest, and fake demo CSV files."""
    manifest_path = initialize_data_catalog(DEFAULT_DATA_ROOT)
    console.print(f"Initialized data catalog: {manifest_path}")


# ---------------------------------------------------------------------------
# Backward-compat wrappers for tests
# ---------------------------------------------------------------------------


def init_data_catalog_fn() -> Path:
    """Initialize the data catalog through a small wrapper for testability."""
    return initialize_data_catalog(DEFAULT_DATA_ROOT)


def seed_demo_data_fn(*, force: bool = False) -> dict[str, int]:
    """Seed demo data through a small wrapper for testability."""
    return _seed_demo_data_fn(DEFAULT_DATA_ROOT, force=force)


@app.command()
def profile_data() -> None:
    """Profile local CSV files under company_data/."""
    if not (DEFAULT_DATA_ROOT / "manifest.json").exists():
        initialize_data_catalog(DEFAULT_DATA_ROOT)
    store = profile_and_save(DEFAULT_DATA_ROOT)
    profile_path = save_profiles(store)
    console.print(f"Profiled datasets: {len(store.profiles)}")
    console.print(f"Saved profiles: {profile_path}")


@app.command()
def inspect_data() -> None:
    """Inspect saved local CSV profile summaries."""
    from decision_system.data_catalog.store import load_profiles  # noqa: PLC0415

    store = load_profiles()
    console.print(render_inspection(inspect_profiles(store)))


@app.command()
def import_datasets(
    source_dir: Path = typer.Option(
        DEFAULT_IMPORT_SOURCE_DIR,
        "--source-dir",
        help="Local ignored folder containing public datasets.",
    ),
    max_rows: int = typer.Option(
        5000,
        "--max-rows",
        min=1,
        help="Maximum rows to write per imported dataset.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Overwrite existing imported CSV outputs.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Inspect what would import without writing CSVs or manifest.",
    ),
) -> None:
    """Convert local public datasets into categorized CSV files."""
    manifest = import_datasets_fn(
        source_dir,
        data_root=DEFAULT_DATA_ROOT,
        max_rows=max_rows,
        force=force,
        dry_run=dry_run,
    )
    console.print(
        f"Imported datasets: {manifest.imported_count}; "
        f"Skipped datasets: {manifest.skipped_count}"
    )
    if not dry_run:
        console.print(
            "Saved import manifest: "
            ".decision_system/imports/import_manifest.json"
        )


@app.command()
def inspect_imports() -> None:
    """Inspect the latest public dataset import manifest."""
    console.print(render_import_manifest(load_import_manifest()))


@app.command()
def seed_demo_data(
    force: bool = typer.Option(
        False,
        "--force",
        help="Overwrite existing demo CSV files.",
    ),
) -> None:
    """Seed company_data/ with synthetic demo CSVs for local testing."""
    summary = seed_demo_data_fn(force=force)
    console.print(
        f"Seeded demo data: {summary['created']} created, "
        f"{summary['overwritten']} overwritten, "
        f"{summary['skipped']} skipped"
    )


# ---------------------------------------------------------------------------
# Hygiene
# ---------------------------------------------------------------------------


def _render_hygiene_report(report: HygieneReport) -> str:
    """Render a hygiene report as ASCII-safe Markdown."""
    lines = [
        "# Repository Hygiene Check",
        "",
        f"Overall: **{report.overall}**",
        "",
    ]
    if report.passed:
        lines.append("## Passed")
        lines.append("")
        for c in report.passed:
            lines.append(f"- [PASS] {c.name}: {c.detail}")
        lines.append("")
    if report.warnings:
        lines.append("## Warnings")
        lines.append("")
        for c in report.warnings:
            lines.append(f"- [WARN] {c.name}: {c.detail}")
        lines.append("")
    if report.failed:
        lines.append("## Failed")
        lines.append("")
        for c in report.failed:
            lines.append(f"- [FAIL] {c.name}: {c.detail}")
        lines.append("")
    summary = (
        f"Passed: {len(report.passed)} | "
        f"Warnings: {len(report.warnings)} | "
        f"Failed: {len(report.failed)}"
    )
    lines.append(summary)
    return "\n".join(lines)


@app.command()
def check_hygiene(
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Print structured JSON instead of Markdown.",
    ),
) -> None:
    """Check repository hygiene for generated files, caches, and agent instructions."""
    report = _run_hygiene_fn(Path.cwd())
    if json_output:
        payload = report.model_dump(mode="json")
        typer.echo(json.dumps(payload, indent=2))
    else:
        console.print(_render_hygiene_report(report))
    if report.overall == "FAIL":
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# Security / Governance sub-commands (v1.2)
# ---------------------------------------------------------------------------
# Each function is decorated at module scope so Typer registers it.
# Heavy security imports are deferred inside each function body so that
# ``--help`` and ``check-hygiene`` remain fast.
# ---------------------------------------------------------------------------

_security_app = typer.Typer(
    name="security",
    help="Security, governance, and audit utilities.",
    no_args_is_help=True,
)
app.add_typer(_security_app)


@_security_app.command("scan-secrets")
def _cmd_scan_secrets(
    path: str = typer.Option(
        ".",
        "--path",
        help="Root path to scan for secrets.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit structured JSON instead of Markdown.",
    ),
) -> None:
    """Scan local files for obvious secrets and credentials."""
    from decision_system.security.audit import append_event  # noqa: PLC0415
    from decision_system.security.inspector import (  # noqa: PLC0415
        inspect_secret_scan,
        render_secret_scan,
    )
    from decision_system.security.secret_scan import (  # noqa: PLC0415
        scan_repo,
    )
    from decision_system.security.store import (  # noqa: PLC0415
        save_secret_scan,
    )

    result = scan_repo(path)
    save_secret_scan(result)
    append_event(
        "secret_scan_run",
        f"Scanned {result.files_scanned} files; {len(result.findings)} findings ({result.overall_status})",
        metadata={
            "files_scanned": result.files_scanned,
            "files_skipped": result.files_skipped,
            "findings_count": len(result.findings),
            "status": result.overall_status,
        },
    )
    if json_output:
        payload = inspect_secret_scan(result)
        typer.echo(json.dumps(payload, indent=2))
    else:
        console.print(render_secret_scan(inspect_secret_scan(result)))


@_security_app.command("redact-preview")
def _cmd_redact_preview(
    text: str = typer.Argument(..., help="Text to preview redacted."),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit structured JSON instead of Markdown.",
    ),
) -> None:
    """Preview PII / secret redactions without modifying any file."""
    from decision_system.security.audit import append_event  # noqa: PLC0415
    from decision_system.security.inspector import (  # noqa: PLC0415
        inspect_redaction,
        render_redaction,
    )
    from decision_system.security.redaction import (  # noqa: PLC0415
        redact,
    )
    from decision_system.security.store import (  # noqa: PLC0415
        save_redaction_result,
    )

    result = redact(text)
    save_redaction_result(result)
    append_event(
        "redact_preview",
        f"Redacted {result.finding_count} spans in preview text",
        metadata={"finding_count": result.finding_count},
    )
    if json_output:
        payload = inspect_redaction(result)
        typer.echo(json.dumps(payload, indent=2))
    else:
        console.print(render_redaction(inspect_redaction(result)))


@_security_app.command("audit-log")
def _cmd_audit_log(
    limit: int = typer.Option(
        20,
        "--limit",
        help="Maximum events to display.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit structured JSON instead of Markdown.",
    ),
) -> None:
    """Inspect the local JSONL audit log."""
    from decision_system.security.audit import (  # noqa: PLC0415
        load_events,
        render_audit_log,
    )

    events = load_events(limit=limit)
    if json_output:
        from decision_system.security.inspector import (  # noqa: PLC0415
            inspect_audit_log,
        )
        payload = inspect_audit_log(events)
        typer.echo(json.dumps(payload, indent=2))
    else:
        console.print(render_audit_log(events, limit=limit))


@_security_app.command("policy-check")
def _cmd_policy_check(
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit structured JSON instead of Markdown.",
    ),
) -> None:
    """Run deterministic policy checks against the repo layout."""
    from decision_system.security.audit import append_event  # noqa: PLC0415
    from decision_system.security.inspector import (  # noqa: PLC0415
        inspect_policy,
        render_policy,
    )
    from decision_system.security.policy import (  # noqa: PLC0415
        run_policy_checks,
    )
    from decision_system.security.store import (  # noqa: PLC0415
        save_policy_result,
    )

    result = run_policy_checks()
    save_policy_result(result)
    append_event(
        "policy_check_run",
        f"Policy check: {result.overall_status.upper()} "
        f"({result.passed_count}/{len(result.checks)} passed)",
        metadata={
            "passed": result.passed_count,
            "failed": result.failed_count,
            "warnings": result.warning_count,
            "status": result.overall_status,
        },
    )
    if json_output:
        payload = inspect_policy(result)
        typer.echo(json.dumps(payload, indent=2))
    else:
        console.print(render_policy(inspect_policy(result)))
    if result.overall_status == "fail":
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# Approval sub-commands (v1.2)
# ---------------------------------------------------------------------------

_approval_app = typer.Typer(
    name="approval",
    help="Local approval-request workflow.",
    no_args_is_help=True,
)
app.add_typer(_approval_app)


@_approval_app.command("request")
def _cmd_approval_request(
    reason: str = typer.Option(
        "user-requested operation",
        "--reason",
        help="Why this approval is needed.",
    ),
    requested_by: str = typer.Option(
        "local-user",
        "--requested-by",
        help="Identity of the requester (no real auth yet).",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit structured JSON instead of Markdown.",
    ),
) -> None:
    """Create a new local approval-request record."""
    from decision_system.security.approvals import (  # noqa: PLC0415
        create_approval,
    )
    from decision_system.security.audit import append_event  # noqa: PLC0415
    from decision_system.security.store import (  # noqa: PLC0415
        save_approval_request,
    )

    request = create_approval(reason, requested_by=requested_by)
    save_approval_request(request)
    append_event(
        "approval_created",
        f"Approval {request.approval_id} created by {requested_by}: {reason}",
        metadata={
            "approval_id": request.approval_id,
            "status": request.status,
            "reason": reason[:200],
        },
    )
    if json_output:
        typer.echo(json.dumps(request.model_dump(mode="json"), indent=2))
    else:
        console.print(
            f"Created approval request: {request.approval_id}\n"
            f"Reason: {reason}\n"
            f"Requested by: {requested_by}\n"
            f"Status: {request.status}\n"
            f"Created: {request.created_at}"
        )


@_approval_app.command("list")
def _cmd_approval_list(
    status: str = typer.Option(
        "pending",
        "--status",
        help="Filter by status: pending, approved, rejected, cancelled.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit structured JSON instead of Markdown.",
    ),
) -> None:
    """List local approval-request records."""
    from decision_system.security.approvals import (  # noqa: PLC0415
        list_approvals,
    )
    from decision_system.security.inspector import (  # noqa: PLC0415
        inspect_approvals,
        render_approvals,
    )

    filter_val: str | None = status if status else None
    requests = list_approvals(status_filter=filter_val)
    if json_output:
        payload = inspect_approvals(requests)
        typer.echo(json.dumps(payload, indent=2))
    else:
        console.print(render_approvals(inspect_approvals(requests)))


@_approval_app.command("inspect")
def _cmd_approval_inspect(
    approval_id: str = typer.Argument(
        ...,
        help="ID of the approval request to inspect.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit structured JSON instead of Markdown.",
    ),
) -> None:
    """Inspect a single local approval-request record."""
    from decision_system.security.approvals import (  # noqa: PLC0415
        inspect_approval,
    )

    request = inspect_approval(approval_id)
    if request is None:
        console.print(f"[red]Approval request not found: {approval_id}[/red]")
        raise typer.Exit(code=1)
    if json_output:
        typer.echo(json.dumps(request.model_dump(mode="json"), indent=2))
    else:
        console.print(f"ID:       {request.approval_id}")
        console.print(f"Reason:   {request.reason}")
        console.print(f"Status:   {request.status}")
        console.print(f"By:       {request.requested_by}")
        console.print(f"Created:  {request.created_at}")
        console.print(f"Resolved: {request.resolved_at or '(active)'}")
        if request.metadata:
            console.print("Metadata:")
            for k, v in request.metadata.items():
                console.print(f"  {k}: {v}")


# ---------------------------------------------------------------------------
# API service
# ---------------------------------------------------------------------------


@app.command("serve-api")
def serve_api(
    host: str = typer.Option(
        "127.0.0.1",
        "--host",
        help="Host interface for the local development API.",
    ),
    port: int = typer.Option(
        8000,
        "--port",
        help="Port for the local development API.",
    ),
    reload: bool = typer.Option(
        False,
        "--reload",
        help="Enable uvicorn auto-reload for local development.",
    ),
) -> None:
    """Run the local FastAPI API for development."""
    import uvicorn  # noqa: PLC0415

    uvicorn.run(
        "decision_system.api.app:app",
        host=host,
        port=port,
        reload=reload,
    )


# ---------------------------------------------------------------------------
# build-context
# ---------------------------------------------------------------------------


@app.command()
def build_context(
    question: str,
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Print structured JSON instead of Markdown.",
    ),
    save: bool = typer.Option(
        False,
        "--save",
        help="Save context to .decision_system/contexts/<run_id>.json.",
    ),
) -> None:
    """Build decision context for a question using local stores."""
    builder = DecisionContextBuilder()
    context = builder.build(question=question)
    saved_path = save_decision_context(context) if save else None
    if json_output:
        payload = context.model_dump(mode="json")
        if saved_path is not None:
            payload["saved_context_path"] = str(saved_path)
        typer.echo(json.dumps(payload, indent=2))
        return
    if saved_path is not None:
        console.print(f"Saved context: {saved_path}")
    summary = inspect_context(context)
    console.print(render_context_inspection(summary))


# ---------------------------------------------------------------------------
# ask (the heaviest command) -- all heavy imports live inside this function.
# ---------------------------------------------------------------------------


@app.command()
def ask(
    question: str,
    top_k: int = typer.Option(
        6,
        "--top-k",
        help="Maximum evidence chunks to retrieve.",
    ),
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
        help="Provider for this run: fake, nvidia_nim, or ollama.",
    ),
    include_insights: bool = typer.Option(
        False,
        "--include-insights",
        help="Add relevant business/data insights to the decision report.",
    ),
    orchestrated: bool = typer.Option(
        False,
        "--orchestrated",
        help="Include orchestration context in the decision report.",
    ),
    save_context_flag: bool = typer.Option(
        False,
        "--save-context",
        help=(
            "Save the decision context to "
            ".decision_system/contexts/<run_id>.json."
        ),
    ),
) -> None:
    """Run the decision workflow for a CLI question.

    All heavy imports (LangGraph, Chroma, agent nodes, RAG, providers,
    eval runners, orchestration, war-room) are loaded lazily inside this
    function so that ``--help`` and ``check-hygiene`` remain fast.
    """
    # Heavy imports: these are the modules that trigger LangGraph, Chroma,
    # pattern detectors, eval runners, and war-room code at import time. Tests
    # monkeypatch the three module-scope symbols above; they do NOT monkeypatch
    # these, so deferring them is safe.
    from decision_system.agents.risk_analyst import (  # noqa: PLC0415
        run_risk_analysis,
    )
    from decision_system.agents.technical_analyst import (  # noqa: PLC0415
        run_technical_analysis,
    )
    from decision_system.evals.runner import (  # noqa: PLC0415
        render_eval_report,
        run_eval_suite,
        save_eval_results,
    )
    from decision_system.graph.workflow import (  # noqa: PLC0415  - LangGraph + agent nodes
        build_workflow,
    )
    from decision_system.graphing.store import (  # noqa: PLC0415
        load_knowledge_graph,
    )
    from decision_system.insights.inspector import (  # noqa: PLC0415
        inspect_insights as _inspect_insights_fn,
        render_insight_inspection,
    )
    from decision_system.insights.store import (  # noqa: PLC0415
        load_insights,
        save_insights,
    )
    from decision_system.ledger.claim_ledger import (  # noqa: PLC0415
        ClaimLedger,
    )
    from decision_system.llm.factory import (  # noqa: PLC0415
        get_provider,
    )
    from decision_system.ontology.inspector import (  # noqa: PLC0415
        inspect_ontology as _inspect_ontology_fn,
        render_ontology_inspection,
    )
    from decision_system.orchestration.judge import (  # noqa: PLC0415
        build_judge_summary,
    )
    from decision_system.orchestration.models import (  # noqa: PLC0415
        JudgeSummary,
        ProblemAnalysis,
    )
    from decision_system.orchestration.store import (  # noqa: PLC0415
        load_latest_session,
    )
    from decision_system.provider_eval.inspector import (  # noqa: PLC0415
        render_provider_eval_suite,
    )
    from decision_system.provider_eval.runner import (  # noqa: PLC0415
        run_provider_eval_suite,
    )
    from decision_system.provider_eval.store import (  # noqa: PLC0415
        load_provider_eval_results,
        save_provider_eval_results,
    )
    from decision_system.provider_experiments.inspector import (  # noqa: PLC0415
        render_provider_experiments,
    )
    from decision_system.provider_experiments.runner import (  # noqa: PLC0415
        load_eval_cases as _load_provider_cases,
        run_experiment_suite,
    )
    from decision_system.provider_experiments.store import (  # noqa: PLC0415
        load_latest_provider_results,
        save_experiment_results,
    )
    from decision_system.rag.chunker import chunk_documents  # noqa: PLC0415
    from decision_system.rag.loader import load_documents  # noqa: PLC0415
    from decision_system.rag.vector_store import (  # noqa: PLC0415
        index_chunks,
        inspect_collection,
    )
    from decision_system.reports.renderer import (  # noqa: PLC0415  - monkeypatched by tests
        render_decision_report,
    )
    from decision_system.war_room.dispatcher import (  # noqa: PLC0415
        build_dispatch_spec as _build_wr_dispatch,
    )
    from decision_system.war_room.evals import (  # noqa: PLC0415
        render_war_room_eval_report,
        run_war_room_eval_suite,
        save_war_room_eval_results,
    )
    from decision_system.war_room.inspector import (  # noqa: PLC0415
        inspect_war_room as _inspect_war_room_impl,
        render_inspection as _render_war_room_inspection,
    )
    from decision_system.war_room.runner import (  # noqa: PLC0415
        run_war_room as _run_war_room_fn,
    )
    from decision_system.war_room.store import (  # noqa: PLC0415
        DEFAULT_RUNS_DIR,
        load_latest_run,
    )

    settings = load_settings()
    active_provider = (provider or settings.provider).strip().lower()

    try:
        get_provider(active_provider, settings=settings)
    except Exception as exc:
        console.print(f"[red]Provider '{active_provider}' is not ready: {exc}[/red]")
        raise typer.Exit(code=1)

    graph = build_workflow()
    graph_input: dict[str, Any] = {
        "run_id": str(uuid4()),
        "question": question,
        "top_k": top_k,
    }
    if provider is not None:
        graph_input["provider"] = active_provider

    # v0.5: Build insight-aware context before running the workflow if requested
    context = None
    saved_context_path = None
    if include_insights or orchestrated or save_context_flag:
        builder = DecisionContextBuilder()
        context = builder.build(question=question, run_id=graph_input["run_id"])
        if save_context_flag:
            saved_context_path = save_decision_context(context)
        if not json_output:
            console.print(f"Saved context: {saved_context_path}")

    try:
        result = graph.invoke(graph_input)
    except Exception as _idx_exc:
        if _is_missing_index_error(_idx_exc):
            console.print(
                "[red]No document index found. "
                "Run [bold]decision-system index[/bold] first, "
                "or add documents to [bold]company_docs/[/bold].[/red]"
            )
            raise typer.Exit(code=1) from _idx_exc
        if active_provider != "fake":
            console.print(
                f"[red]Provider '{active_provider}' run failed: {_idx_exc}[/red]"
            )
            raise typer.Exit(code=1)
        raise

    saved_path = _save_run(result) if save_run else None

    # v0.5: Inject context into the report for insight-aware rendering
    if context is not None and (include_insights or orchestrated):
        from decision_system.models import DecisionReport  # noqa: PLC0415

        _render_report_fn_ref = render_decision_report
        report = result.get("final_report")
        if isinstance(report, DecisionReport):
            report_context = _report_context(
                context,
                include_insights=include_insights,
                include_orchestration=orchestrated,
            )
            new_report = _render_report_fn_ref(
                question=question,
                run_id=result.get("run_id", context.run_id),
                claims=result.get("claims", []),
                context=report_context,
            )
            result["final_report"] = new_report

    if json_output:
        payload = _ask_json_payload(result)
        if saved_path is not None:
            payload["saved_run_path"] = str(saved_path)
        if saved_context_path is not None:
            payload["saved_context_path"] = str(saved_context_path)
        if context is not None:
            payload["decision_context"] = context.model_dump(mode="json")
        typer.echo(json.dumps(payload, indent=2))
        return
    if show_evidence:
        typer.echo(_render_evidence_section(result.get("retrieved_evidence", [])))
        typer.echo()
        typer.echo(result["final_report"].markdown)
        if saved_path is not None:
            typer.echo(f"Saved run: {saved_path}")
    elif json_output:
        pass  # already handled above
    else:
        # Default: print the Markdown report
        typer.echo(result["final_report"].markdown)
        if saved_path is not None:
            typer.echo(f"Saved run: {saved_path}")


# ---------------------------------------------------------------------------
# War-cabinet commands (v0.6)
# ---------------------------------------------------------------------------


@app.command()
def plan_war_room(question: str) -> None:
    """Plan a war-cabinet run without executing agents."""
    from decision_system.war_room.dispatcher import (  # noqa: PLC0415
        build_dispatch_spec as _build_wr_dispatch,
    )

    spec = _build_wr_dispatch(question)
    ctx = spec.higher_context
    analysis = ctx.problem_analysis
    console.print(f"Run ID: {ctx.run_id}")
    console.print(f"Question: {ctx.question}")
    console.print(
        f"Decision type: {analysis.get('decision_type', 'unknown')}"
    )
    console.print(
        f"Selected roles: {', '.join(spec.dispatch_order) or 'none'}"
    )
    console.print(
        f"Skipped roles: {', '.join(spec.skipped_roles) or 'none'}"
    )
    categories_str = ", ".join(ctx.required_data_categories)
    console.print(
        f"Required data categories: {categories_str or 'none'}"
    )
    concepts_str = ", ".join(ctx.required_ontology_concepts)
    console.print(
        f"Required ontology concepts: {concepts_str or 'none'}"
    )
    console.print(f"Allowed tools: {', '.join(ctx.allowed_tools) or 'none'}")
    if spec.missing_inputs:
        console.print("Missing inputs:")
        for item in spec.missing_inputs:
            console.print(f" - {item}")


@app.command()
def run_war_room(
    question: str,
) -> None:
    """Run a complete war-cabinet simulation."""
    from decision_system.war_room.runner import (  # noqa: PLC0415
        run_war_room as _run_war_room_fn,
    )
    from decision_system.war_room.store import (  # noqa: PLC0415
        DEFAULT_RUNS_DIR,
    )

    run = _run_war_room_fn(question)
    console.print(f"Run ID: {run.run_id}")
    console.print(f"Question: {run.question}")
    console.print(
        f"Selected roles: "
        f"{', '.join(run.dispatch_spec.dispatch_order) or 'none'}"
    )
    artifact_count = len(run.workspace.artifacts) if run.workspace else 0
    console.print(f"Artifact count: {artifact_count}")
    console.print(f"Judge intervention count: {len(run.judge_interventions)}")
    human_review = sum(
        1
        for i in run.judge_interventions
        if i.requires_human_review
    )
    console.print(f"Human review required: {human_review}")
    for artifact in (
        run.workspace.artifacts if run.workspace else []
    ):
        console.print(
            f" - {artifact.title} (confidence={artifact.confidence})"
        )
    for intervention in run.judge_interventions:
        tag = (
            "REQUIRES HUMAN REVIEW"
            if intervention.requires_human_review
            else "FYI"
        )
        console.print(
            f" [{tag} {intervention.severity.upper()}] "
            f"{intervention.reason}"
        )
    saved = DEFAULT_RUNS_DIR / f"{run.run_id}.json"
    if saved.exists():
        console.print(f"Saved war-room run: {saved}")


@app.command()
def inspect_war_room() -> None:
    """Inspect the latest saved war-room run."""
    from decision_system.war_room.inspector import (  # noqa: PLC0415
        inspect_war_room as _inspect_war_room_impl,
        render_inspection as _render_war_room_inspection,
    )
    from decision_system.war_room.store import (  # noqa: PLC0415
        load_latest_run,
    )

    run = load_latest_run()
    if run is None:
        console.print(
            "No war-room run found. Run `decision-system run-war-room` first."
        )
        return
    summary = _inspect_war_room_impl(run)
    console.print(_render_war_room_inspection(summary))


# ---------------------------------------------------------------------------
# Provider experiment commands (v0.7)
# ---------------------------------------------------------------------------


@app.command()
def provider_health() -> None:
    """Print provider configuration health status."""
    settings = load_settings()
    lines: list[str] = []
    lines.append(f"Configured provider: {settings.provider}")
    lines.append("")
    lines.append("fake: always available (offline default)")
    lines.append("")

    nim_key_ok = bool(settings.nvidia_api_key)
    nim_model_ok = bool(settings.nvidia_nim_model)
    nim_status = "configured" if (nim_key_ok and nim_model_ok) else "incomplete"
    lines.append(f"nvidia_nim: {nim_status}")
    lines.append(
        f" API key: {'present' if nim_key_ok else 'missing'}"
    )
    lines.append(
        f" model: {'present' if nim_model_ok else 'missing'} "
        f"({settings.nvidia_nim_model or 'unset'})"
    )
    lines.append(f" base URL: {settings.nvidia_nim_base_url}")
    lines.append("")

    ollama_model_ok = bool(settings.ollama_model)
    ollama_status = "configured" if ollama_model_ok else "incomplete"
    lines.append(f"ollama: {ollama_status}")
    lines.append(f" base URL: {settings.ollama_base_url}")
    lines.append(
        f" model: {'present' if ollama_model_ok else 'missing'} "
        f"({settings.ollama_model or 'unset'})"
    )
    lines.append(f" timeout: {settings.ollama_timeout_seconds}s")
    lines.append("")
    console.print("\n".join(lines))


@app.command()
def provider_smoke(
    provider: str = typer.Option(
        "fake",
        "--provider",
        help="Provider to smoke-test: fake, nvidia_nim, or ollama.",
    ),
) -> None:
    """Run one small in-memory evidence case against a provider."""
    from decision_system.llm.factory import (  # noqa: PLC0415
        get_provider,
    )
    from decision_system.models import (  # noqa: PLC0415
        AgentMemo,
        Claim,
        EvidenceChunk,
    )

    settings = load_settings()
    try:
        target_provider = get_provider(provider, settings=settings)
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)
    except Exception as exc:
        console.print(f"[red]Provider init failed: {exc}[/red]")
        raise typer.Exit(code=1)

    evidence = [
        EvidenceChunk(
            evidence_id="smoke-e1",
            document_id="smoke",
            source_path="smoke",
            source_filename="smoke.txt",
            chunk_id="smoke-chunk-0001",
            text=(
                "Billing migration requires rollback planning "
                "and staged deployment."
            ),
            score=0.95,
        )
    ]
    question = "Should we migrate billing?"

    tech_valid = False
    risk_valid = False
    claims_valid = False
    errors: list[str] = []
    tech: AgentMemo | None = None
    risk: AgentMemo | None = None

    try:
        tech = target_provider.technical_memo(question, evidence)
        tech_valid = isinstance(tech, AgentMemo)
        if not tech_valid:
            errors.append(f"technical_memo returned {type(tech).__name__}")
    except Exception as exc:
        errors.append(f"technical_memo: {exc}")

    try:
        tech_stub = (
            tech
            if isinstance(tech, AgentMemo)
            else AgentMemo(
                agent_name="technical_analyst",
                question=question,
                summary="(stub)",
                claims=[],
                risks=[],
                options=[],
                cited_evidence_ids=[],
            )
        )
        risk = target_provider.risk_memo(question, evidence, tech_stub)
        risk_valid = isinstance(risk, AgentMemo)
        if not risk_valid:
            errors.append(f"risk_memo returned {type(risk).__name__}")
    except Exception as exc:
        errors.append(f"risk_memo: {exc}")

    try:
        memos: list[AgentMemo] = []
        if isinstance(tech, AgentMemo):
            memos.append(tech)
        if isinstance(risk, AgentMemo):
            memos.append(risk)
        claims = target_provider.extract_claims("smoke-run", memos)
        claims_valid = isinstance(claims, list) and all(
            isinstance(c, Claim) for c in claims
        )
    except Exception as exc:
        errors.append(f"extract_claims: {exc}")

    if errors:
        console.print("[red]Smoke test FAILED:[/red]")
        for error in errors:
            console.print(f" - {error}")
        raise typer.Exit(code=1)

    console.print(
        f"[green]Smoke test PASSED[/green] for provider '{provider}'."
    )
    console.print(f" technical_memo: {tech_valid}")
    console.print(f" risk_memo: {risk_valid}")
    console.print(f" extract_claims: {claims_valid}")


@app.command("eval-provider")
def evaluate_provider(
    provider: str = typer.Option(
        "fake",
        "--provider",
        help="Provider to evaluate: fake, nvidia_nim, or ollama.",
    ),
    json_output: bool = typer.Option(False, "--json"),
    save_results: bool = typer.Option(False, "--save-results"),
    require_configured: bool = typer.Option(
        False,
        "--require-configured",
        help=(
            "Fail instead of skipping when NIM/Ollama "
            "are not configured."
        ),
    ),
) -> None:
    """Run provider experiment evaluation cases for a selected provider."""
    from decision_system.provider_experiments.inspector import (  # noqa: PLC0415
        render_provider_experiments,
    )
    from decision_system.provider_experiments.runner import (  # noqa: PLC0415
        load_eval_cases as _load_provider_cases,
        run_experiment_suite,
    )
    from decision_system.provider_experiments.store import (  # noqa: PLC0415
        save_experiment_results,
    )

    settings = load_settings()
    if provider not in {"fake", "nvidia_nim", "ollama"}:
        console.print(
            f"[red]Unknown provider '{provider}'. "
            "Expected one of: fake, nvidia_nim, ollama.[/red]"
        )
        raise typer.Exit(code=1)

    if provider != "fake":
        if provider == "nvidia_nim":
            if not settings.nvidia_api_key or not settings.nvidia_nim_model:
                if require_configured:
                    console.print(
                        "[red]nvidia_nim is not configured "
                        "(missing API key or model).[/red]"
                    )
                    raise typer.Exit(code=1)
                console.print(
                    "Skipping: nvidia_nim is not configured "
                    "(missing API key or model)."
                )
                return
        elif provider == "ollama":
            if not settings.ollama_model:
                if require_configured:
                    console.print(
                        "[red]ollama is not configured "
                        "(missing OLLAMA_MODEL).[/red]"
                    )
                    raise typer.Exit(code=1)
                console.print(
                    "Skipping: ollama is not configured "
                    "(missing OLLAMA_MODEL)."
                )
                return

    cases = _load_provider_cases()
    if not cases:
        console.print(
            "No provider experiment cases found under "
            "evals/provider_cases/."
        )
        return

    suite = run_experiment_suite(
        cases, provider_name=provider, settings=settings
    )
    if save_results:
        output_path = save_experiment_results(suite)
        console.print(f"Saved results: {output_path}")
    if json_output:
        typer.echo(suite.model_dump_json(indent=2))
    else:
        console.print(render_provider_experiments(suite))
    if suite.failed_cases > 0:
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# Provider evaluation commands (v0.7.1)
# ---------------------------------------------------------------------------


@app.command()
def eval_providers(
    provider: str | None = typer.Option(
        None,
        "--provider",
        help=(
            "Provider to evaluate: fake, nvidia_nim, or ollama. "
            "Defaults to all."
        ),
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help=(
            "Print structured provider evaluation JSON "
            "instead of text."
        ),
    ),
    save_results: bool = typer.Option(
        False,
        "--save-results",
        help=(
            "Save results to "
            ".decision_system/provider_evals/provider_eval_results.json."
        ),
    ),
    manual_real_provider: bool = typer.Option(
        False,
        "--manual-real-provider",
        help=(
            "Explicitly allow real NIM/Ollama provider calls "
            "instead of mocked evaluation."
        ),
    ),
) -> None:
    """Compare fake, NVIDIA NIM, and Ollama provider behavior safely."""
    from decision_system.provider_eval.inspector import (  # noqa: PLC0415
        render_provider_eval_suite,
    )
    from decision_system.provider_eval.runner import (  # noqa: PLC0415
        run_provider_eval_suite,
    )
    from decision_system.provider_eval.store import (  # noqa: PLC0415
        save_provider_eval_results,
    )

    suite = run_provider_eval_suite(
        provider_name=provider,
        manual_real_provider=manual_real_provider,
    )
    if save_results:
        saved_path = save_provider_eval_results(suite)
        suite = suite.model_copy(
            update={"saved_result_path": str(saved_path)}
        )
    if json_output:
        typer.echo(suite.model_dump_json(indent=2))
    else:
        console.print(render_provider_eval_suite(suite))
    if suite.failed_cases > 0:
        raise typer.Exit(code=1)


@app.command()
def inspect_provider_evals() -> None:
    """Inspect the latest saved provider evaluation results."""
    from decision_system.provider_eval.inspector import (  # noqa: PLC0415
        render_provider_eval_suite,
    )
    from decision_system.provider_eval.store import (  # noqa: PLC0415
        load_provider_eval_results,
    )

    suite = load_provider_eval_results()
    if suite is None:
        console.print(
            "No provider evaluation results found. "
            "Run `decision-system eval-providers --save-results` first."
        )
        return
    console.print(render_provider_eval_suite(suite))


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------


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
    from decision_system.evals.runner import (  # noqa: PLC0415
        render_eval_report,
        run_eval_suite,
        save_eval_results,
    )

    suite_result = run_eval_suite()
    if save_results:
        suite_result = save_eval_results(suite_result)
    if json_output:
        typer.echo(suite_result.model_dump_json(indent=2))
    else:
        typer.echo(render_eval_report(suite_result))
    if not suite_result.passed:
        raise typer.Exit(code=1)


@app.command("eval-war-room")
def evaluate_war_room(
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Print structured evaluation JSON instead of text.",
    ),
    save_results: bool = typer.Option(
        False,
        "--save-results",
        help=(
            "Save war-room eval results under "
            ".decision_system/evals/."
        ),
    ),
) -> None:
    """Run war-room offline evaluation cases with quality gates."""
    from decision_system.war_room.evals import (  # noqa: PLC0415
        render_war_room_eval_report,
        run_war_room_eval_suite,
        save_war_room_eval_results,
    )

    suite = run_war_room_eval_suite()
    if save_results:
        suite = save_war_room_eval_results(suite)
    if json_output:
        typer.echo(json.dumps(suite.model_dump(mode="json"), indent=2))
    else:
        typer.echo(render_war_room_eval_report(suite))
    if suite.failed_cases > 0:
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# Report context helper (used inside the ask command)
# ---------------------------------------------------------------------------


def _report_context(
    context: DecisionContext,
    *,
    include_insights: bool,
    include_orchestration: bool,
) -> DecisionContext:
    """Return a context view containing only report sections requested by flags."""
    human_review_items = list(context.human_review_items)
    if not include_orchestration:
        human_review_items = [
            item
            for item in human_review_items
            if not item.startswith("Judge ")
        ]
    return DecisionContext(
        run_id=context.run_id,
        question=context.question,
        problem_analysis=context.problem_analysis,
        relevant_data_categories=context.relevant_data_categories,
        relevant_storage_tiers=context.relevant_storage_tiers,
        relevant_ontology_concepts=context.relevant_ontology_concepts,
        relevant_insights=(
            context.relevant_insights if include_insights else []
        ),
        graph_signals=(
            context.graph_signals
            if include_insights or include_orchestration
            else []
        ),
        orchestration_summary=(
            context.orchestration_summary
            if include_orchestration
            else {}
        ),
        judge_summary=(
            context.judge_summary if include_orchestration else {}
        ),
        human_review_items=human_review_items,
        created_at=context.created_at,
    )
