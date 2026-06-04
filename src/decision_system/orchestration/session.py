"""Session manager for the v0.4 orchestration layer.

Creates DecisionSession records and persists orchestration runs to disk.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from decision_system.orchestration.models import DecisionSession

DEFAULT_RUNS_DIR = Path(".decision_system") / "orchestration" / "runs"
DEFAULT_RUNS_FILENAME = "latest.json"


def _runs_dir(base: Path | str = DEFAULT_RUNS_DIR) -> Path:
    return Path(base)


def create_session(
    question: str,
    *,
    context_summary: str = "",
    required_data_categories: list[str] | None = None,
    required_tools: list[str] | None = None,
    relevant_roles: list[str] | None = None,
    storage_tiers_used: list[str] | None = None,
) -> DecisionSession:
    """Create a new DecisionSession with a fresh run_id."""

    return DecisionSession(
        session_id=str(uuid.uuid4()),
        run_id=str(uuid.uuid4()),
        question=question,
        context_summary=context_summary,
        required_data_categories=required_data_categories or [],
        required_tools=required_tools or [],
        relevant_roles=relevant_roles or [],
        storage_tiers_used=storage_tiers_used or [],
    )


def load_latest_run(runs_dir: Path | str = DEFAULT_RUNS_DIR) -> DecisionSession | None:
    """Load the most recently saved orchestration run, or None."""

    d = _runs_dir(runs_dir)
    path = d / DEFAULT_RUNS_FILENAME
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return DecisionSession.model_validate(raw)
    except Exception:  # noqa: BLE001
        return None


# Alias for CLI compatibility
load_latest_session = load_latest_run
