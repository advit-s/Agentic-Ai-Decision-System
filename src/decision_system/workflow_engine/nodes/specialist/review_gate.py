"""ReviewGateNode — pauses workflow for human review of intermediate results.

When executed, this node stores the data for review and returns a
"pending_review" status. The workflow engine marks the execution as
"awaiting_review" until a human approves, rejects, or requests changes.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from decision_system.workflow_engine.models import WorkflowNode, ExecutionContext


_APPROVED = "approved"
_REJECTED = "rejected"
_PENDING_REVIEW = "pending_review"
_SKIPPED = "skipped"

import os as _os
_REVIEWS_DIR = Path(
    _os.environ.get("DECISION_SYSTEM_DATA_DIR", ".decision_system")
) / "reviews"


def _ensure_reviews_dir() -> Path:
    """Create the reviews directory if it does not exist."""
    _REVIEWS_DIR.mkdir(parents=True, exist_ok=True)
    return _REVIEWS_DIR


def _save_review(review: dict[str, Any]) -> None:
    """Persist a review record to the local filesystem."""
    reviews_dir = _ensure_reviews_dir()
    review_id = review["review_id"]
    path = reviews_dir / f"{review_id}.json"
    with open(path, "w") as f:
        json.dump(review, f, indent=2, default=str)


def _load_review(review_id: str) -> dict[str, Any] | None:
    """Load a review record from the local filesystem."""
    path = _REVIEWS_DIR / f"{review_id}.json"
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


# ── Review Gate Node ─────────────────────────────────────────────────


class ReviewGateNode(WorkflowNode):
    """Pause the workflow for human review of intermediate results.

    Stores the submitted data and returns a ``pending_review`` status.
    A human reviewer must later approve, reject, or request changes
    via the review API before the workflow can continue.
    """

    type: str = "decision_system.review_gate"
    label: str = "Review Gate"

    async def execute(self, inputs: dict, ctx: ExecutionContext) -> dict:
        data = inputs.get("data")
        instructions = inputs.get("instructions", "")
        reviewers = inputs.get("reviewers", [])

        if data is None:
            return {
                "status": _SKIPPED,
                "approved": True,
                "review_notes": "No data to review — automatically approved.",
            }

        review_id = uuid4().hex[:12]
        now = datetime.now().isoformat()

        review_record: dict[str, Any] = {
            "review_id": review_id,
            "workflow_id": ctx.workflow_id,
            "execution_id": ctx.execution_id,
            "status": _PENDING_REVIEW,
            "data": data,
            "instructions": instructions,
            "reviewers": reviewers if isinstance(reviewers, list) else [],
            "created_at": now,
            "resolved_at": None,
            "action": None,
            "review_notes": None,
            "modified_data": None,
            "reviewed_by": None,
        }

        _save_review(review_record)

        return {
            "status": _PENDING_REVIEW,
            "review_id": review_id,
            "data": data,
            "instructions": instructions,
            "reviewers": reviewers if isinstance(reviewers, list) else [],
            "created_at": now,
        }

    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "require_notes": {
                    "type": "boolean",
                    "default": True,
                    "title": "Require Review Notes",
                },
                "allow_edit": {
                    "type": "boolean",
                    "default": True,
                    "title": "Allow Data Editing",
                },
                "timeout_hours": {
                    "type": "integer",
                    "default": 72,
                    "minimum": 1,
                    "maximum": 8760,
                    "title": "Timeout (hours)",
                },
            },
        }

    @classmethod
    def get_input_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "data": {
                    "type": "object",
                    "description": "Data requiring review",
                },
                "instructions": {
                    "type": "string",
                    "description": "Review instructions/context",
                },
                "reviewers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Suggested reviewers",
                },
            },
        }

    @classmethod
    def get_output_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "approved": {"type": "boolean"},
                "review_notes": {"type": "string"},
                "modified_data": {"type": "object"},
                "reviewed_by": {"type": "string"},
                "reviewed_at": {"type": "string"},
                "status": {"type": "string"},
            },
        }


# ── Helper functions for API layer ──────────────────────────────────


def list_pending_reviews() -> list[dict[str, Any]]:
    """List all review records with status ``pending_review``."""
    reviews_dir = _ensure_reviews_dir()
    results: list[dict[str, Any]] = []
    if not reviews_dir.exists():
        return results
    for path in sorted(reviews_dir.iterdir()):
        if path.suffix == ".json":
            try:
                with open(path) as f:
                    review = json.load(f)
                results.append(review)
            except (json.JSONDecodeError, OSError):
                continue
    return results


def list_all_reviews() -> list[dict[str, Any]]:
    """List all review records regardless of status."""
    reviews_dir = _ensure_reviews_dir()
    results: list[dict[str, Any]] = []
    if not reviews_dir.exists():
        return results
    for path in sorted(reviews_dir.iterdir()):
        if path.suffix == ".json":
            try:
                with open(path) as f:
                    review = json.load(f)
                results.append(review)
            except (json.JSONDecodeError, OSError):
                continue
    return results


def resolve_review(
    review_id: str,
    action: str,
    notes: str = "",
    modified_data: dict[str, Any] | None = None,
    reviewed_by: str | None = None,
) -> dict[str, Any] | None:
    """Resolve a pending review with the given action.

    Returns the updated review record, or ``None`` if the review_id
    does not exist. Raises ``ValueError`` if the review is already
    resolved.
    """
    review = _load_review(review_id)
    if review is None:
        return None

    if review.get("status") != _PENDING_REVIEW:
        raise ValueError(f"Review '{review_id}' is already resolved (status={review.get('status')})")

    now = datetime.now().isoformat()

    review["status"] = _PENDING_REVIEW  # will be overridden below
    if action == _APPROVED:
        review["status"] = _APPROVED
        review["approved"] = True
    elif action == _REJECTED:
        review["status"] = _REJECTED
        review["approved"] = False
    else:
        review["status"] = "changes_requested"
        review["approved"] = False

    review["action"] = action
    review["review_notes"] = notes or ""
    review["modified_data"] = modified_data
    review["reviewed_by"] = reviewed_by or "system"
    review["resolved_at"] = now

    _save_review(review)
    return review
