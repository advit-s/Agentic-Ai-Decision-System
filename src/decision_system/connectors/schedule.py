"""Connector schedule model and store (v1.29).

Supports manual, interval, and cron schedule types for connector sync.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class ConnectorSchedule(BaseModel):
    """Schedule for automated connector sync."""

    schedule_id: str = Field(default_factory=lambda: str(uuid4()))
    workspace_id: str | None = None
    connector_id: str
    enabled: bool = True
    schedule_type: str = "manual"  # manual | interval | cron
    interval_minutes: int | None = None
    cron_expression: str | None = None
    next_run_at: datetime | None = None
    last_run_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)

    def calculate_next_run(self) -> datetime | None:
        """Calculate the next run time based on schedule type and last_run."""
        now = datetime.now(timezone.utc)
        if not self.enabled:
            return None
        if self.schedule_type == "manual":
            return None
        if self.schedule_type == "interval":
            if self.interval_minutes is None or self.interval_minutes < 1:
                return None
            base = self.last_run_at or self.created_at
            return base + timedelta(minutes=self.interval_minutes)
        if self.schedule_type == "cron":
            if self.interval_minutes:
                base = self.last_run_at or self.created_at
                return base + timedelta(minutes=self.interval_minutes)
            return None
        return None

    def is_due(self) -> bool:
        """Check if this schedule is due for execution."""
        if not self.enabled:
            return False
        if self.schedule_type == "manual":
            return False
        next_run = self.next_run_at
        if next_run is None:
            next_run = self.calculate_next_run()
        if next_run is None:
            return False
        return datetime.now(timezone.utc) >= next_run


class ScheduleStore:
    """Persistent JSON-backed store for connector schedules."""

    def __init__(self, base_dir: str | Path | None = None) -> None:
        self._base_dir = Path(base_dir) if base_dir else Path(".decision_system") / "connectors" / "schedules"
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def _store_path(self, workspace_id: str | None, connector_id: str) -> Path:
        scope = workspace_id if workspace_id else "_global"
        d = self._base_dir / scope
        d.mkdir(parents=True, exist_ok=True)
        return d / f"{connector_id}.json"

    def _load_all(self, workspace_id: str | None, connector_id: str):
        path = self._store_path(workspace_id, connector_id)
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return [ConnectorSchedule(**item) for item in data]
        except Exception:
            return []

    def _save_all(self, workspace_id: str | None, connector_id: str, schedules: list[ConnectorSchedule]):
        path = self._store_path(workspace_id, connector_id)
        data = [s.model_dump(mode="json") for s in schedules]
        path.write_text(json.dumps(data, indent=2, default=str) + "\n", encoding="utf-8")

    def list_schedules(self, workspace_id: str | None, connector_id: str) -> list[ConnectorSchedule]:
        return self._load_all(workspace_id, connector_id)

    def get_schedule(self, workspace_id: str | None, connector_id: str, schedule_id: str) -> ConnectorSchedule | None:
        for s in self._load_all(workspace_id, connector_id):
            if s.schedule_id == schedule_id:
                return s
        return None

    def create_schedule(self, workspace_id: str | None, schedule: ConnectorSchedule) -> ConnectorSchedule:
        schedules = self._load_all(workspace_id, schedule.connector_id)
        schedule.next_run_at = schedule.calculate_next_run()
        schedules.append(schedule)
        self._save_all(workspace_id, schedule.connector_id, schedules)
        return schedule

    def update_schedule(self, workspace_id: str | None, schedule: ConnectorSchedule) -> ConnectorSchedule | None:
        schedules = self._load_all(workspace_id, schedule.connector_id)
        found = False
        for i, s in enumerate(schedules):
            if s.schedule_id == schedule.schedule_id:
                schedule.updated_at = datetime.now(timezone.utc)
                schedule.next_run_at = schedule.calculate_next_run()
                schedules[i] = schedule
                found = True
                break
        if not found:
            return None
        self._save_all(workspace_id, schedule.connector_id, schedules)
        return schedule

    def delete_schedule(self, workspace_id: str | None, connector_id: str, schedule_id: str) -> bool:
        schedules = self._load_all(workspace_id, connector_id)
        filtered = [s for s in schedules if s.schedule_id != schedule_id]
        if len(filtered) == len(schedules):
            return False
        self._save_all(workspace_id, connector_id, filtered)
        return True

    def toggle_schedule(self, workspace_id: str | None, connector_id: str, schedule_id: str) -> ConnectorSchedule | None:
        s = self.get_schedule(workspace_id, connector_id, schedule_id)
        if s is None:
            return None
        s.enabled = not s.enabled
        s.updated_at = datetime.now(timezone.utc)
        s.next_run_at = s.calculate_next_run()
        return self.update_schedule(workspace_id, s)

    def list_due_schedules(self) -> list[ConnectorSchedule]:
        """List all schedules across all workspaces that are due."""
        due: list[ConnectorSchedule] = []
        if not self._base_dir.exists():
            return due
        for scope_dir in sorted(self._base_dir.iterdir()):
            if not scope_dir.is_dir() or scope_dir.name.startswith("."):
                continue
            ws_id = scope_dir.name if scope_dir.name != "_global" else None
            for f in scope_dir.glob("*.json"):
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    for item in data:
                        s = ConnectorSchedule(**item)
                        if s.is_due():
                            due.append(s)
                except Exception:
                    continue
        return due

    def find_schedule_for_connector(
        self, workspace_id: str | None, connector_id: str
    ) -> ConnectorSchedule | None:
        schedules = self._load_all(workspace_id, connector_id)
        return schedules[0] if schedules else None


# Module-level singleton
_default_store: ScheduleStore | None = None


def get_schedule_store() -> ScheduleStore:
    global _default_store
    if _default_store is None:
        _default_store = ScheduleStore()
    return _default_store


def reset_schedule_store() -> None:
    global _default_store
    _default_store = None
