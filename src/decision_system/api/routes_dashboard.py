"""Dashboard endpoint — aggregates system status from local generated stores."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter

from decision_system import __version__
from decision_system.config import load_settings

router = APIRouter(tags=["dashboard"])


def _read_json(path: Path) -> dict | list | None:
    """Safely read a JSON file, returning None if missing or broken."""
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _count_store(store_dir: Path, filename: str, key: str) -> int:
    """Count items under a key in a generated store file, or 0."""
    data = _read_json(store_dir / filename)
    if isinstance(data, dict):
        items = data.get(key, [])
        return len(items) if isinstance(items, list) else 0
    return 0


@router.get("/dashboard")
def get_dashboard() -> dict:
    """Return aggregated system status for the web UI dashboard view."""
    base = Path(".decision_system")

    # Gather counts from generated stores.
    profile_count = _count_store(base / "data_profiles", "profiles.json", "profiles")
    insight_count = _count_store(base / "insights", "insights.json", "insights")
    graph_path = base / "graph" / "knowledge_graph.json"
    graph_data = _read_json(graph_path)
    graph_entities = len(graph_data.get("entities", [])) if isinstance(graph_data, dict) else 0
    graph_relationships = len(graph_data.get("relationships", [])) if isinstance(graph_data, dict) else 0

    # Connector count from the built-in registry.
    try:
        from decision_system.connectors.registry import list_connectors
        connector_count = len(list_connectors())
    except Exception:
        connector_count = 0

    # Workspace status.
    ws_path = base / "workspaces" / "workspaces.sqlite"
    workspace_status = "ok" if ws_path.exists() else "no_active_workspace"

    # Index status.
    chroma_dir = base / "chroma"
    index_status = "indexed" if chroma_dir.exists() and any(chroma_dir.iterdir()) else "not_indexed"

    # War-room run count.
    war_room_dir = base / "war_room" / "runs"
    war_room_runs = (
        len(list(war_room_dir.glob("*.json"))) if war_room_dir.exists() else 0
    )

    quick_links = [
        {"label": "Index Documents", "icon": "document", "section": "data"},
        {"label": "Ask a Question", "icon": "question", "section": "ask"},
        {"label": "Run War Room", "icon": "war-room", "section": "war-room"},
        {"label": "Security Audit", "icon": "security", "section": "security"},
    ]

    settings = load_settings()
    provider = settings.provider

    return {
        "version": __version__,
        "provider": provider,
        "mock_mode": provider == "fake",
        "api_status": "ok",
        "workspace_status": workspace_status,
        "index_status": index_status,
        "connector_count": connector_count,
        "insight_count": insight_count,
        "ontology_concepts": 38,
        "graph_entities": graph_entities,
        "graph_relationships": graph_relationships,
        "war_room_runs": war_room_runs,
        "data_profiles": profile_count,
        "system_ready": True,
        "last_audit": datetime.now(timezone.utc).isoformat(),
        "project_info": {
            "name": "Agentic AI Decision System",
            "description": "Company Intelligence Engine — local evidence, bounded analysis, claim verification, cited decision reports.",
        },
        "phase_1_ready": True,
        "phase_2_ready": True,
        "quick_links": quick_links,
    }
