"""Batch import processing for connectors (v1.31).

Processes large item lists in bounded batches with progress persistence,
checkpoint-based resume, and cancel support.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable

from decision_system.connectors.models import (
    ConnectorFetchedContent,
    ConnectorImportJob,
    ConnectorRuntimeItem,
)
from decision_system.connectors.rate_limiter import (
    RateLimiter,
    get_rate_limiter,
)
from decision_system.connectors.retry_policy import (
    RetryPolicy,
    get_retry_policy,
)
from decision_system.connectors.store import ConnectorJobStore, save_job

logger = logging.getLogger(__name__)


@dataclass
class BatchResult:
    """Result of processing a single batch."""

    batch_number: int
    items_processed: int = 0
    items_imported: int = 0
    items_skipped: int = 0
    items_changed: int = 0
    items_failed: int = 0
    items_rate_limited: int = 0
    duration_ms: float = 0.0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class BatchProcessor:
    """Processes connector imports in bounded batches with progress tracking.

    Features:
    - Configurable batch size (default 50)
    - Progress persisted after each batch
    - Partial failures don't lose progress
    - Checkpoint-based resume for paused/failed jobs
    - Cancel support (checks between batches)
    - Retry and rate-limit integration
    """

    def __init__(
        self,
        batch_size: int = 50,
        retry_policy: RetryPolicy | None = None,
        rate_limiter: RateLimiter | None = None,
        job_store: ConnectorJobStore | None = None,
    ) -> None:
        self.batch_size = batch_size
        self.retry_policy = retry_policy or get_retry_policy()
        self.rate_limiter = rate_limiter or get_rate_limiter()
        self.job_store = job_store or ConnectorJobStore()

    def process_items(
        self,
        job: ConnectorImportJob,
        items: list[ConnectorRuntimeItem],
        fetch_fn: Callable[[ConnectorRuntimeItem], ConnectorFetchedContent],
        progress_callback: Callable[[ConnectorImportJob], None] | None = None,
    ) -> ConnectorImportJob:
        """Process items in bounded batches with progress tracking.

        Args:
            job: Import job to update with progress.
            items: Full list of items to process.
            fetch_fn: Function to fetch a single item's content.
            progress_callback: Optional callback after each batch.

        Returns:
            Updated job with final status.
        """
        start_time = time.time()
        total = len(items)

        # Initialize job
        job.status = "running"
        job.total_items = total
        job.items_found = total
        job.processed_items = 0
        job.items_imported = 0
        job.items_skipped = 0
        job.items_failed = 0
        job.changed_items = 0
        job.unchanged_items = 0
        job.rate_limited_items = 0
        job.current_batch = 0
        job.started_at = datetime.now(timezone.utc)
        save_job(job)

        # Determine starting offset from checkpoint (for resume)
        start_offset = job.resume_from_checkpoint.get("processed_items", 0)
        if start_offset > 0:
            logger.info(
                "Resuming job %s from checkpoint: %d/%d items already processed",
                job.job_id,
                start_offset,
                total,
            )
            job.processed_items = start_offset

        total_batches = max(1, (total + self.batch_size - 1) // self.batch_size)

        for batch_num in range(1, total_batches + 1):
            # Check for cancel between batches
            if job.cancel_requested:
                job.status = "cancelled"
                job.completed_at = datetime.now(timezone.utc)
                job.duration_ms = (time.time() - start_time) * 1000
                save_job(job)
                logger.info("Job %s cancelled after batch %d", job.job_id, batch_num)
                return job

            # Skip already-processed items (for resume)
            start_idx = (batch_num - 1) * self.batch_size
            if start_idx < start_offset:
                continue

            batch_items = items[start_idx : start_idx + self.batch_size]
            if not batch_items:
                break

            batch_result = self._process_batch(job, batch_num, batch_items, fetch_fn)

            # Update job with batch results
            job.current_batch = batch_num
            job.processed_items += batch_result.items_processed
            job.items_imported += batch_result.items_imported
            job.items_skipped += batch_result.items_skipped
            job.changed_items += batch_result.items_changed
            job.items_failed += batch_result.items_failed
            job.rate_limited_items += batch_result.items_rate_limited
            job.errors.extend(batch_result.errors[:10])  # cap errors
            job.warnings.extend(batch_result.warnings[:10])

            # Save checkpoint for resume
            job.resume_from_checkpoint = {
                "processed_items": job.processed_items,
                "batch_number": batch_num,
                "total_items": total,
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }

            # Persist progress
            save_job(job)

            # Call progress callback
            if progress_callback:
                progress_callback(job)

        # Finalize job
        job.duration_ms = (time.time() - start_time) * 1000
        job.completed_at = datetime.now(timezone.utc)

        if job.items_failed > 0:
            job.status = "completed_with_warnings"
        else:
            job.status = "completed"

        save_job(job)
        logger.info(
            "Job %s completed: %d/%d items, %d failed",
            job.job_id,
            job.items_imported,
            total,
            job.items_failed,
        )
        return job

    def _process_batch(
        self,
        job: ConnectorImportJob,
        batch_num: int,
        batch_items: list[ConnectorRuntimeItem],
        fetch_fn: Callable[[ConnectorRuntimeItem], ConnectorFetchedContent],
    ) -> BatchResult:
        """Process a single batch of items."""
        batch_start = time.time()
        result = BatchResult(batch_number=batch_num)

        for item in batch_items:
            # Check rate limit before each item
            if self.rate_limiter.check_rate_limited(job.connector_id):
                retry_after = self.rate_limiter.get_retry_after(job.connector_id)
                result.items_rate_limited += 1
                result.warnings.append(f"Rate-limited, retry-after: {retry_after:.0f}s")
                logger.info(
                    "Rate-limited during batch %d, item %s, retry-after: %.0fs",
                    batch_num,
                    item.external_id,
                    retry_after,
                )
                continue

            # Update current item
            job.current_item_id = item.external_id
            result.items_processed += 1

            try:
                # Fetch with retry
                content, attempts = self.retry_policy.execute_with_retry(
                    fetch_fn,
                    item,
                )

                if content and (content.content_text or content.content_bytes):
                    result.items_imported += 1
                else:
                    # Empty content - skip with warning
                    result.items_skipped += 1
                    result.warnings.append(f"Item '{item.external_id}' returned empty content")

            except Exception as e:
                error_str = str(e)
                result.items_failed += 1
                result.errors.append(f"Item '{item.external_id}': {error_str}")

                # Check if this was a rate-limit error
                if any(
                    kw in error_str.lower() for kw in ("429", "rate limit", "too many requests")
                ):
                    result.items_rate_limited += 1
                    self.rate_limiter.record_429(job.connector_id, source_url=item.source_url or "")

        result.duration_ms = (time.time() - batch_start) * 1000
        return result

    def request_cancel(self, job: ConnectorImportJob) -> ConnectorImportJob:
        """Request cancellation of a running job."""
        job.cancel_requested = True
        save_job(job)
        return job

    def resume_job(
        self,
        job: ConnectorImportJob,
        items: list[ConnectorRuntimeItem],
        fetch_fn: Callable[[ConnectorRuntimeItem], ConnectorFetchedContent],
    ) -> ConnectorImportJob:
        """Resume a failed or paused job from its checkpoint."""
        if job.status not in ("failed", "paused", "cancelled"):
            logger.warning("Job %s is not in a resumable state: %s", job.job_id, job.status)
            return job

        job.status = "running"
        job.cancel_requested = False
        return self.process_items(job, items, fetch_fn)


# Default singleton
_default_processor: BatchProcessor | None = None


def get_batch_processor() -> BatchProcessor:
    global _default_processor
    if _default_processor is None:
        _default_processor = BatchProcessor()
    return _default_processor


def reset_batch_processor() -> None:
    global _default_processor
    _default_processor = None
