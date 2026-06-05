"""v0.6 War-Cabinet Agent Context Protocol models."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Literal
from pydantic import BaseModel, Field

ConfidenceLevel = Literal["low", "medium", "high"]
RoleType = Literal[
    "financial_analyst",
    "customer_analyst",
    "sales_analyst",
    "marketing_analyst",
    "product_analyst",
    "operations_analyst",
    "strategy_analyst",
    "technical_analyst",
    "legal_analyst",
    "risk_analyst",
    "judge",
    "unknown",
]
ArtifactType = Literal[
    "analysis", "risk_assessment", "recommendation",
    "data_quality", "dependency", "market", "legal", "judgment", "general",
]


class FrozenDict(dict):
    """Dictionary that rejects mutation after construction."""

    def _blocked(self, *_args: Any, **_kwargs: Any) -> None:
        raise TypeError("higher context is read-only")

    __setitem__ = _blocked
    __delitem__ = _blocked
    clear = _blocked
    pop = _blocked
    popitem = _blocked
    setdefault = _blocked
    update = _blocked


def _freeze_value(value: Any) -> Any:
    """Recursively convert mutable containers into read-only containers."""

    if isinstance(value, FrozenDict):
        return value
    if isinstance(value, dict):
        return FrozenDict({key: _freeze_value(item) for key, item in value.items()})
    if isinstance(value, list | tuple):
        return tuple(_freeze_value(item) for item in value)
    return value


class HigherContext(BaseModel):
    """Immutable read-only context shared by all war-room agents."""
    model_config = {"frozen": True}

    run_id: str
    question: str
    problem_analysis: dict[str, Any] = Field(default_factory=dict)
    decision_context_summary: str = ""
    required_data_categories: tuple[str, ...] = Field(default_factory=tuple)
    required_ontology_concepts: tuple[str, ...] = Field(default_factory=tuple)
    relevant_insight_ids: tuple[str, ...] = Field(default_factory=tuple)
    relevant_storage_tiers: tuple[str, ...] = Field(default_factory=tuple)
    constraints: tuple[str, ...] = Field(default_factory=tuple)
    allowed_tools: tuple[str, ...] = Field(default_factory=tuple)
    evidence_requirements: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def model_post_init(self, __context: Any) -> None:
        """Deep-freeze nested dictionaries so the shared context is read-only."""

        object.__setattr__(self, "problem_analysis", _freeze_value(self.problem_analysis))
        object.__setattr__(self, "evidence_requirements", _freeze_value(self.evidence_requirements))


class PersonalAgentContext(BaseModel):
    """Read-only context for one specialist agent."""
    model_config = {"frozen": True}

    agent_id: str
    role_name: str
    role_type: RoleType = "unknown"
    assigned_task: str = ""
    perspective: str = ""
    allowed_tools: tuple[str, ...] = Field(default_factory=tuple)
    focus_areas: tuple[str, ...] = Field(default_factory=tuple)
    higher_context_ref: str = ""
    private_notes: str = ""
    output_requirements: dict[str, Any] = Field(default_factory=dict)

    def model_post_init(self, __context: Any) -> None:
        """Prevent mutation of nested output requirements."""

        object.__setattr__(self, "output_requirements", _freeze_value(self.output_requirements))


class WorkspaceArtifact(BaseModel):
    """One artifact written to the append-only common workspace."""
    model_config = {"frozen": True}

    artifact_id: str
    run_id: str
    author_agent_id: str = ""
    artifact_type: ArtifactType = "general"
    title: str = ""
    content: str = ""
    evidence_ids: tuple[str, ...] = Field(default_factory=tuple)
    insight_ids: tuple[str, ...] = Field(default_factory=tuple)
    ontology_concepts: tuple[str, ...] = Field(default_factory=tuple)
    confidence: ConfidenceLevel = "medium"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CommonWorkspace(BaseModel):
    """Append-only common workspace. No agent can delete externally-written artifacts."""
    model_config = {"extra": "forbid", "frozen": True}

    run_id: str
    artifacts: tuple[WorkspaceArtifact, ...] = Field(default_factory=tuple)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def add_artifact(self, artifact: WorkspaceArtifact) -> None:
        """Append-only: never remove or replace existing artifacts."""
        if artifact.run_id != self.run_id:
            raise ValueError("workspace artifact run_id must match workspace run_id")
        object.__setattr__(self, "artifacts", self.artifacts + (artifact,))
        object.__setattr__(self, "updated_at", datetime.now(timezone.utc).isoformat())


class AgentDispatchSpec(BaseModel):
    """Spec for dispatching specialist agents."""
    run_id: str
    higher_context: HigherContext
    personal_contexts: list[PersonalAgentContext] = Field(default_factory=list)
    dispatch_order: list[str] = Field(default_factory=list)
    skipped_roles: list[str] = Field(default_factory=list)
    missing_inputs: list[str] = Field(default_factory=list)


class AgentRunResult(BaseModel):
    """Result of running one specialist agent."""
    agent_id: str
    role_name: str
    status: str = "completed"  # completed | skipped | failed
    artifacts_created: int = 0
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class JudgeIntervention(BaseModel):
    """A judge flag against a workspace artifact."""
    intervention_id: str
    run_id: str
    target_artifact_id: str
    severity: str = "medium"  # low | medium | high | critical
    reason: str = ""
    recommended_action: str = ""
    requires_human_review: bool = False


class WarRoomRun(BaseModel):
    """Full record of one war-room execution."""
    run_id: str
    question: str
    higher_context: HigherContext | None = None
    dispatch_spec: AgentDispatchSpec | None = None
    workspace: CommonWorkspace | None = None
    agent_results: list[AgentRunResult] = Field(default_factory=list)
    judge_interventions: list[JudgeIntervention] = Field(default_factory=list)
    final_summary: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
