"""Schedule models for workflow triggers."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TriggerType(str, Enum):
    """Supported trigger types for automated workflow execution."""

    CRON = "cron"
    WEBHOOK = "webhook"
    FILE_WATCH = "file_watch"


class ScheduleDefinition(BaseModel):
    """A schedule that triggers a workflow automatically.

    Each schedule links a trigger type + configuration to a workflow.
    Multiple schedules can target the same workflow with different triggers.
    A workflow can have at most one webhook schedule (the webhook path
    is generated and bound to that schedule).

    The scheduler polls enabled schedules and evaluates their trigger
    conditions. When a condition is met, the associated workflow is
    executed via DAGEngine.
    """

    id: str = Field(
        default="",
        description="Unique schedule identifier (auto-generated on save)",
    )
    workflow_id: str = Field(
        ...,
        description="ID of the workflow to execute",
    )
    trigger_type: TriggerType = Field(
        default=TriggerType.CRON,
        description="Type of trigger that activates this schedule",
    )
    trigger_config: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Trigger-specific configuration. For cron: {'expression': '0 9 * * 1-5'}. "
            "For webhook: {'path': '/hooks/my-webhook'}. "
            "For file_watch: {'directory': 'company_docs/', 'pattern': '*.md'}"
        ),
    )
    enabled: bool = Field(
        default=True,
        description="Whether this schedule is active and should be evaluated",
    )
    last_fired: datetime | None = Field(
        default=None,
        description="Timestamp of the last time this schedule fired",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When this schedule was created",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When this schedule was last updated",
    )
