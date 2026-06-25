"""Persistence for war-room runs."""

from __future__ import annotations

import json
from pathlib import Path
from decision_system._data_root import get_data_root
from typing import Any

from decision_system.war_room.models import WarRoomRun

def get_default_runs_dir() -> Path:
    """Return the war room runs directory (lazy)."""
    return get_data_root() / "war_room" / "runs"


def _json_default(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    raise TypeError(f"Cannot serialize {type(value)!r}")


def save_war_room_run(
    run: WarRoomRun, runs_dir: Path | None = None
) -> Path:
    """Persist a WarRoomRun as JSON."""
    dir_ = runs_dir or get_default_runs_dir()
    dir_.mkdir(parents=True, exist_ok=True)
    payload = run.model_dump(mode="json")
    run_path = dir_ / f"{run.run_id}.json"
    run_path.write_text(
        json.dumps(payload, indent=2, default=_json_default) + "\n",
        encoding="utf-8",
    )
    return run_path.resolve()


def load_war_room_run(
    run_id: str, runs_dir: Path | None = None
) -> WarRoomRun | None:
    """Load a single WarRoomRun by run_id."""
    dir_ = runs_dir or get_default_runs_dir()
    path = dir_ / f"{run_id}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return WarRoomRun.model_validate(data)


def load_latest_run(runs_dir: Path | None = None) -> WarRoomRun | None:
    """Load the most recently created war-room run."""
    dir_ = runs_dir or get_default_runs_dir()
    if not dir_.exists():
        return None
    candidates = sorted(
        dir_.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True
    )
    if not candidates:
        return None
    data = json.loads(candidates[0].read_text(encoding="utf-8"))
    return WarRoomRun.model_validate(data)
