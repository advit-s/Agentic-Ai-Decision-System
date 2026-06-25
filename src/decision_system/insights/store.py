"""Persist and load the deterministic insight store as local JSON."""

from __future__ import annotations

import json
from pathlib import Path

from decision_system._data_root import get_data_root
from decision_system.insights.models import InsightStore


def _default_insights_dir() -> Path:
    return get_data_root() / "insights"


DEFAULT_INSIGHTS_FILENAME = "insights.json"


def _insights_path(store_dir: Path | str | None = None) -> Path:
    if store_dir is None:
        store_dir = _default_insights_dir()
    return Path(store_dir) / DEFAULT_INSIGHTS_FILENAME


def save_insights(store: InsightStore, store_dir: Path | str | None = None) -> Path:
    """Write the insight store to ``.decision_system/insights/insights.json``."""
    if store_dir is None:
        store_dir = _default_insights_dir()
    path = _insights_path(store_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(store.model_dump(mode="json"), indent=2) + "\n", encoding="utf-8")
    return path.resolve()


def load_insights(store_dir: Path | str | None = None) -> InsightStore:
    """Load insights from disk, returning an empty store if the file is missing."""
    if store_dir is None:
        store_dir = _default_insights_dir()
    path = _insights_path(store_dir)
    if not path.exists():
        return InsightStore()
    raw = json.loads(path.read_text(encoding="utf-8"))
    return InsightStore.model_validate(raw)
