"""Persist and load the deterministic insight store as local JSON."""

from __future__ import annotations

import json
from pathlib import Path

from decision_system.insights.models import InsightStore

DEFAULT_INSIGHTS_DIR = Path(".decision_system") / "insights"
DEFAULT_INSIGHTS_FILENAME = "insights.json"


def _insights_path(store_dir: Path | str = DEFAULT_INSIGHTS_DIR) -> Path:
    return Path(store_dir) / DEFAULT_INSIGHTS_FILENAME


def save_insights(store: InsightStore, store_dir: Path | str = DEFAULT_INSIGHTS_DIR) -> Path:
    """Write the insight store to ``.decision_system/insights/insights.json``."""
    path = _insights_path(store_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(store.model_dump(mode="json"), indent=2) + "\n", encoding="utf-8")
    return path.resolve()


def load_insights(store_dir: Path | str = DEFAULT_INSIGHTS_DIR) -> InsightStore:
    """Load insights from disk, returning an empty store if the file is missing."""
    path = _insights_path(store_dir)
    if not path.exists():
        return InsightStore()
    raw = json.loads(path.read_text(encoding="utf-8"))
    return InsightStore.model_validate(raw)
