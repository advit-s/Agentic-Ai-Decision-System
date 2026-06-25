"""Persist and load DecisionContext as local JSON."""

from __future__ import annotations

import json
from pathlib import Path
from decision_system._data_root import get_data_root

from decision_system.context.models import DecisionContext


def _get_context_dir() -> Path:
    """Return the context directory (lazy)."""
    return get_data_root() / "contexts"

DEFAULT_CONTEXT_DIR = _get_context_dir()


def _context_path(run_id: str, store_dir: Path | str = DEFAULT_CONTEXT_DIR) -> Path:
    return Path(store_dir) / f"{run_id}.json"


def save_context(
    context: DecisionContext,
    store_dir: Path | str = DEFAULT_CONTEXT_DIR,
) -> Path:
    """Write the decision context to ``.decision_system/contexts/<run_id>.json``."""
    path = _context_path(context.run_id, store_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(context.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )
    return path.resolve()


def load_context(
    run_id: str,
    store_dir: Path | str = DEFAULT_CONTEXT_DIR,
) -> DecisionContext | None:
    """Load a decision context from disk, returning None if missing."""
    path = _context_path(run_id, store_dir)
    if not path.exists():
        return None
    raw = json.loads(path.read_text(encoding="utf-8"))
    return DecisionContext.model_validate(raw)