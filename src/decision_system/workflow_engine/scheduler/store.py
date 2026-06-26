"""Schedule store — persists schedule definitions as JSON files."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import uuid4

from decision_system.workflow_engine.scheduler.models import (
    ScheduleDefinition,
    TriggerType,
)


def get_default_schedule_dir() -> Path:
    from decision_system._data_root import get_data_root

    return get_data_root() / "schedules"


class ScheduleStore:
    """JSON file-backed store for ScheduleDefinition objects.

    Each schedule is stored as a single JSON file:
    ``<store_dir>/schedule_<id>.json``

    Usage::

        store = ScheduleStore(get_default_schedule_dir())
        sd = store.save(ScheduleDefinition(workflow_id="wf-1"))
        loaded = store.load(sd.id)
        all_schedules = store.list()
        store.delete(sd.id)
    """

    def __init__(self, store_dir: str | Path) -> None:
        self._dir = Path(store_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    @property
    def store_dir(self) -> Path:
        """The directory where schedule files are stored."""
        return self._dir

    def _path(self, schedule_id: str) -> Path:
        return self._dir / f"schedule_{schedule_id}.json"

    def _all_paths(self) -> list[Path]:
        if not self._dir.exists():
            return []
        return sorted(self._dir.glob("schedule_*.json"))

    def save(self, schedule: ScheduleDefinition) -> ScheduleDefinition:
        """Save a schedule definition. Generates an ID if missing.

        Returns the saved schedule with the generated ID and
        updated ``updated_at`` timestamp.
        """
        if not schedule.id:
            schedule.id = f"sch-{uuid4().hex[:12]}"
        schedule.updated_at = datetime.now(timezone.utc)
        self._path(schedule.id).write_text(
            json.dumps(schedule.model_dump(mode="json"), indent=2, default=str),
        )
        return schedule

    def load(self, schedule_id: str) -> Optional[ScheduleDefinition]:
        """Load a schedule by its ID. Returns ``None`` if not found."""
        path = self._path(schedule_id)
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        return ScheduleDefinition(**data)

    def list(
        self,
        workflow_id: Optional[str] = None,
        trigger_type: Optional[TriggerType] = None,
    ) -> list[ScheduleDefinition]:
        """List all schedules, optionally filtered by workflow ID or trigger type.

        Returns an empty list if no schedules exist.
        """
        results: list[ScheduleDefinition] = []
        for path in self._all_paths():
            data = json.loads(path.read_text())
            sd = ScheduleDefinition(**data)
            if workflow_id is not None and sd.workflow_id != workflow_id:
                continue
            if trigger_type is not None and sd.trigger_type != trigger_type:
                continue
            results.append(sd)
        return results

    def delete(self, schedule_id: str) -> bool:
        """Delete a schedule by ID. Returns ``True`` if it existed."""
        path = self._path(schedule_id)
        if path.exists():
            path.unlink()
            return True
        return False

    def update_last_fired(
        self,
        schedule_id: str,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """Update the ``last_fired`` timestamp without a full load/save cycle.

        If ``timestamp`` is ``None``, uses the current UTC time.
        Does nothing if the schedule does not exist.
        """
        sd = self.load(schedule_id)
        if sd is not None:
            sd.last_fired = timestamp or datetime.now(timezone.utc)
            self.save(sd)
