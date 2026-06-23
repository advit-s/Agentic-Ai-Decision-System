"""Abstract store interfaces for workflow definitions and execution states."""

from __future__ import annotations

from abc import ABC, abstractmethod

from decision_system.workflow_engine.models import (
    WorkflowDefinition, ExecutionState,
)


class WorkflowStore(ABC):
    """Persistent storage for workflow definitions."""

    @abstractmethod
    def save(self, workflow: WorkflowDefinition) -> None: ...

    @abstractmethod
    def load(self, workflow_id: str) -> WorkflowDefinition | None: ...

    @abstractmethod
    def list(self) -> list[WorkflowDefinition]: ...

    @abstractmethod
    def delete(self, workflow_id: str) -> None: ...


class ExecutionStore(ABC):
    """Persistent storage for execution states."""

    @abstractmethod
    def save(self, state: ExecutionState) -> None: ...

    @abstractmethod
    def load(self, execution_id: str) -> ExecutionState | None: ...

    @abstractmethod
    def list(self, workflow_id: str | None = None) -> list[ExecutionState]: ...

    @abstractmethod
    def delete(self, execution_id: str) -> None: ...

    @abstractmethod
    def delete(self, execution_id: str) -> None: ...
