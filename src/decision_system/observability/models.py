"""Observability models for metrics, eval history, quality reports, and trace summaries."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class MetricType(str, Enum):
    """Types of metrics collected."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


class EvalStatus(str, Enum):
    """Evaluation run status."""

    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


class QualityDimension(str, Enum):
    """Quality report dimensions."""

    CORRECTNESS = "correctness"
    COMPLETENESS = "completeness"
    CONSISTENCY = "consistency"
    CITATION_GROUNDING = "citation_grounding"
    HALLUCINATION_RISK = "hallucination_risk"
    CONTRADICTION_HANDLING = "contradiction_handling"
    UNSUPPORTED_CLAIMS = "unsupported_claims"
    RESPONSE_TIME = "response_time"
    TOKEN_USAGE = "token_usage"


@dataclass
class MetricPoint:
    """Single metric datapoint."""

    name: str
    value: float
    metric_type: MetricType
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    labels: dict[str, str] = field(default_factory=dict)


@dataclass
class MetricSummary:
    """Aggregated metric summary."""

    name: str
    count: int
    sum: float
    min: float
    max: float
    avg: float
    p50: float = 0.0
    p95: float = 0.0
    p99: float = 0.0


class EvalRunRecord(BaseModel):
    """Record of a single evaluation run."""

    run_id: str = Field(default_factory=lambda: str(uuid4()))
    eval_type: str  # "local", "provider", "war_room", etc.
    status: EvalStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    total_cases: int = 0
    passed_cases: int = 0
    failed_cases: int = 0
    skipped_cases: int = 0
    error_cases: int = 0
    duration_seconds: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)
    case_results: list[dict[str, Any]] = Field(default_factory=list)


class QualityReport(BaseModel):
    """Quality assessment report."""

    report_id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    target_type: str  # "eval_run", "provider", "workflow", etc.
    target_id: str
    overall_score: float  # 0.0 - 1.0
    overall_status: str  # "pass", "warn", "fail"
    dimension_scores: dict[QualityDimension, float] = Field(default_factory=dict)
    dimension_details: dict[QualityDimension, dict[str, Any]] = Field(default_factory=dict)
    recommendations: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TraceSummary(BaseModel):
    """Summary of a workflow/agent trace."""

    trace_id: str = Field(default_factory=lambda: str(uuid4()))
    workflow_type: str  # "decision", "orchestration", "war_room", etc.
    question: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0.0
    node_count: int = 0
    nodes_executed: list[str] = Field(default_factory=list)
    node_durations: dict[str, float] = Field(default_factory=dict)
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    error_count: int = 0
    errors: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ObservabilityStorePaths(BaseModel):
    """Paths for observability storage."""

    root: str
    metrics: str
    eval_history: str
    quality_reports: str
    traces: str