"""Persist and load orchestration DecisionSession runs."""

from __future__ import annotations

import json
from pathlib import Path

from decision_system._data_root import get_data_root
from decision_system.orchestration.models import DecisionSession


def _get_runs_dir() -> Path:
    """Return the orchestration runs directory (lazy)."""
    return get_data_root() / "orchestration" / "runs"


LATEST_FILENAME = "latest.json"


def _runs_dir(base: Path | str | None = None) -> Path:
    if base is None:
        base = get_data_root() / "orchestration" / "runs"
    return Path(base)


def save_decision_session(
    session: DecisionSession,
    runs_dir: Path | str | None = None,
) -> Path:
    """Write a DecisionSession to ``<runs_dir>/<run_id>.json`` and update
    ``<runs_dir>/latest.json``."""

    d = _runs_dir(runs_dir)
    d.mkdir(parents=True, exist_ok=True)

    run_path = d / f"{session.run_id}.json"
    run_path.write_text(
        json.dumps(session.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )

    latest_path = d / LATEST_FILENAME
    latest_path.write_text(
        json.dumps(session.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )

    return run_path.resolve()


def load_decision_session(
    run_id: str,
    runs_dir: Path | str = _get_runs_dir(),
) -> DecisionSession | None:
    """Load a specific run by its run_id, or None on miss."""

    d = _runs_dir(runs_dir)
    path = d / f"{run_id}.json"
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return DecisionSession.model_validate(raw)
    except Exception:  # noqa: BLE001
        return None


def load_latest_session(
    runs_dir: Path | str | None = None,
) -> DecisionSession | None:
    """Load the latest run (latest.json), or None."""

    d = _runs_dir(runs_dir)
    path = d / LATEST_FILENAME
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return DecisionSession.model_validate(raw)
    except Exception:  # noqa: BLE001
        return None


def list_runs(
    runs_dir: Path | str = _get_runs_dir(),
) -> list[dict[str, str]]:
    """Return a summary of all saved run files (not latest.json)."""

    d = _runs_dir(runs_dir)
    if not d.exists():
        return []
    runs: list[dict[str, str]] = []
    for p in sorted(d.glob("*.json")):
        if p.name == LATEST_FILENAME:
            continue
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
            runs.append(
                {
                    "run_id": raw.get("run_id", "?"),
                    "question": raw.get("question", "?"),
                    "status": raw.get("status", "?"),
                    "created_at": raw.get("created_at", ""),
                }
            )
        except Exception:  # noqa: BLE001
            pass
    return runs
