"""Data API router — exposes profiles, graph, and ontology data."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter


router = APIRouter(tags=["data"])


def _read_json(path: Path) -> dict | list | None:
    """Safely read a JSON file, returning None if missing or broken."""
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


# ---------------------------------------------------------------------------
# Data Profiles
# ---------------------------------------------------------------------------


@router.get("/data-profiles")
def get_data_profiles() -> dict:
    """Return profiled CSV data from the generated data-profiles store."""
    profiles_path = Path(".decision_system") / "data_profiles" / "profiles.json"
    data = _read_json(profiles_path) or {}
    return {
        "generated_at": data.get("generated_at") or datetime.now(timezone.utc).isoformat(),
        "profiles": data.get("profiles", []),
    }


# ---------------------------------------------------------------------------
# Knowledge Graph
# ---------------------------------------------------------------------------


@router.get("/graph")
def get_graph() -> dict:
    """Return the extracted knowledge graph entities and relationships."""
    graph_path = Path(".decision_system") / "graph" / "knowledge_graph.json"
    data = _read_json(graph_path) or {}
    return {
        "generated_at": data.get("generated_at") or datetime.now(timezone.utc).isoformat(),
        "entities": data.get("entities", []),
        "relationships": data.get("relationships", []),
    }
