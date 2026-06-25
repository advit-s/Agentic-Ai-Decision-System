"""JSON file-backed claim store.

Provides durable local storage for claims, linked to workspace, execution,
and workflow IDs. Claims persist across restarts under the configured
data directory.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from decision_system.models import Claim


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
    path.write_text(json.dumps(data, indent=2, default=str, ensure_ascii=False))


class JSONClaimStore:
    """Persistent claim store backed by JSON files.

    Each claim is stored as a JSON file under the configured directory.
    An index file tracks all claim IDs for efficient listing.
    """

    def __init__(self, store_dir: Path) -> None:
        self._dir = store_dir / "claims"
        _ensure_dir(self._dir)

    def _path(self, claim_id: str) -> Path:
        return self._dir / f"{claim_id}.json"

    def _index_path(self) -> Path:
        return self._dir / "_index.json"

    def _load_index(self) -> list[str]:
        data = _read_json(self._index_path())
        return data if isinstance(data, list) else []

    def _save_index(self, ids: list[str]) -> None:
        _write_json(self._index_path(), ids)

    def save(self, claim: Claim) -> None:
        """Save or update a claim."""
        # Ensure updated_at is set
        if not claim.updated_at:
            claim.updated_at = datetime.now(timezone.utc)
        _write_json(self._path(claim.claim_id), claim.model_dump(mode="json"))
        ids = self._load_index()
        if claim.claim_id not in ids:
            ids.append(claim.claim_id)
            self._save_index(ids)

    def load(self, claim_id: str) -> Claim | None:
        """Load a claim by ID."""
        data = _read_json(self._path(claim_id))
        if data is None:
            return None
        return Claim(**data)

    def list(
        self,
        workspace_id: str | None = None,
        execution_id: str | None = None,
        workflow_id: str | None = None,
    ) -> list[Claim]:
        """List claims, optionally filtered by workspace, execution, or workflow."""
        claims: list[Claim] = []
        for cid in self._load_index():
            c = self.load(cid)
            if c is None:
                continue
            if workspace_id is not None and c.workspace_id != workspace_id:
                continue
            if execution_id is not None and c.execution_id != execution_id:
                continue
            if workflow_id is not None and c.workflow_id != workflow_id:
                continue
            claims.append(c)
        return claims

    def delete(self, claim_id: str) -> None:
        """Delete a claim by ID."""
        path = self._path(claim_id)
        if path.exists():
            path.unlink()
        ids = self._load_index()
        if claim_id in ids:
            ids.remove(claim_id)
            self._save_index(ids)

    def count(
        self,
        workspace_id: str | None = None,
        execution_id: str | None = None,
    ) -> int:
        """Count claims, optionally filtered."""
        return len(self.list(workspace_id=workspace_id, execution_id=execution_id))

    def summary(
        self,
        workspace_id: str | None = None,
        execution_id: str | None = None,
    ) -> dict[str, Any]:
        """Return a summary of claim statuses."""
        claims = self.list(workspace_id=workspace_id, execution_id=execution_id)
        total = len(claims)
        supported = sum(1 for c in claims if c.status == "supported")
        contradicted = sum(1 for c in claims if c.status == "contradicted")
        unsupported = sum(1 for c in claims if c.status == "unsupported")
        uncertain = sum(1 for c in claims if c.status == "uncertain")
        pending = sum(1 for c in claims if c.status == "pending")
        claims_with_evidence = sum(1 for c in claims if c.evidence_ids or c.evidence_snippets)
        return {
            "total": total,
            "supported": supported,
            "contradicted": contradicted,
            "unsupported": unsupported,
            "uncertain": uncertain,
            "pending": pending,
            "claims_with_evidence": claims_with_evidence,
            "claims_without_evidence": total - claims_with_evidence,
            "evidence_coverage_score": round(supported / total, 2) if total > 0 else 0.0,
            "evidence_coverage_score_v2": round(claims_with_evidence / total, 2)
            if total > 0
            else 0.0,
        }

    def add_claim(
        self,
        claim_text: str,
        source_agent: str,
        claim_type: str = "assumption",
        status: str | None = None,
        confidence: str | None = None,
        evidence_ids: list[str] | None = None,
        source_ids: list[str] | None = None,
        chunk_ids: list[str] | None = None,
        evidence_snippets: list[str] | None = None,
        contradicting_evidence_ids: list[str] | None = None,
        review_required: bool | None = None,
        review_status: str | None = None,
        metadata: dict[str, str] | None = None,
        workspace_id: str | None = None,
        execution_id: str | None = None,
        workflow_id: str | None = None,
        node_id: str | None = None,
        run_id: str | None = None,
    ) -> Claim:
        """Create and save a new claim."""
        claim = Claim(
            claim_id=str(uuid4()),
            run_id=run_id or "",
            workspace_id=workspace_id,
            execution_id=execution_id,
            workflow_id=workflow_id,
            node_id=node_id,
            source_agent=source_agent,
            claim_text=claim_text,
            claim_type=claim_type,  # type: ignore
            status=status or "pending",  # type: ignore
            confidence=confidence or "low",  # type: ignore
            evidence_ids=evidence_ids or [],
            source_ids=source_ids or [],
            chunk_ids=chunk_ids or [],
            evidence_snippets=evidence_snippets or [],
            contradicting_evidence_ids=contradicting_evidence_ids or [],
            review_required=review_required or False,
            review_status=review_status,
            metadata=metadata or {},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self.save(claim)
        return claim
