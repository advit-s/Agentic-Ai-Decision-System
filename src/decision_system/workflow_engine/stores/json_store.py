"""JSON file-based implementations of workflow and execution stores."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from decision_system.workflow_engine.models import (
    WorkflowDefinition, ExecutionState,
)
from decision_system.workflow_engine.stores.base import (
    WorkflowStore, ExecutionStore,
)


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def _write_json(path: Path, data: Any) -> None:
    _ensure_dir(path.parent)
    path.write_text(json.dumps(data, indent=2, default=str))


class JSONWorkflowStore(WorkflowStore):
    """Workflow store backed by JSON files under a directory."""

    def __init__(self, store_dir: Path) -> None:
        self._dir = store_dir / "workflows"
        _ensure_dir(self._dir)

    def _path(self, workflow_id: str) -> Path:
        return self._dir / f"{workflow_id}.json"

    def _index_path(self) -> Path:
        return self._dir / "_index.json"

    def _load_index(self) -> list[str]:
        data = _read_json(self._index_path())
        return data if isinstance(data, list) else []

    def _save_index(self, ids: list[str]) -> None:
        _write_json(self._index_path(), ids)

    def save(self, workflow: WorkflowDefinition) -> None:
        _write_json(self._path(workflow.id), workflow.model_dump(mode="json"))
        ids = self._load_index()
        if workflow.id not in ids:
            ids.append(workflow.id)
            self._save_index(ids)

    def load(self, workflow_id: str) -> WorkflowDefinition | None:
        data = _read_json(self._path(workflow_id))
        if data is None:
            return None
        return WorkflowDefinition(**data)

    def list(self) -> list[WorkflowDefinition]:
        workflows: list[WorkflowDefinition] = []
        for wf_id in self._load_index():
            wf = self.load(wf_id)
            if wf is not None:
                workflows.append(wf)
        return workflows

    def delete(self, workflow_id: str) -> None:
        path = self._path(workflow_id)
        if path.exists():
            path.unlink()
        ids = self._load_index()
        if workflow_id in ids:
            ids.remove(workflow_id)
            self._save_index(ids)


class JSONExecutionStore(ExecutionStore):
    """Execution store backed by JSON files under a directory."""

    def __init__(self, store_dir: Path) -> None:
        self._dir = store_dir / "executions"
        _ensure_dir(self._dir)

    def _path(self, execution_id: str) -> Path:
        return self._dir / f"{execution_id}.json"

    def save(self, state: ExecutionState) -> None:
        _write_json(self._path(state.execution_id), state.model_dump(mode="json"))

    def load(self, execution_id: str) -> ExecutionState | None:
        data = _read_json(self._path(execution_id))
        if data is None:
            return None
        return ExecutionState(**data)

    def list(self, workflow_id: str | None = None) -> list[ExecutionState]:
        states: list[ExecutionState] = []
        if not self._dir.exists():
            return states
        for f in sorted(self._dir.iterdir()):
            if f.suffix != ".json":
                continue
            state = self.load(f.stem)
            if state is not None:
                if workflow_id is None or state.workflow_id == workflow_id:
                    states.append(state)
        return states
