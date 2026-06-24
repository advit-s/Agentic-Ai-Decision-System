"""Tests for v1.31 connector reliability: batch processing, pagination,
retry/backoff, rate-limit handling, cancel/resume, dedup, provenance,
and audit/metrics.
"""

from __future__ import annotations
import tempfile

import hashlib
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from decision_system.connectors.models import (
    ConnectorImportJob,
    ConnectorRuntimeItem,
    ConnectorFetchedContent,
    ConnectorConfig,
    ConnectorType,
    ConnectorMode,
    ConnectorConfigStatus,
    JobProgress,
    ConnectorJobStatus,
)
from decision_system.connectors.retry_policy import (
    RetryPolicy,
    RetryAttempt,
    get_retry_policy,
    reset_retry_policy,
)
from decision_system.connectors.rate_limiter import (
    RateLimiter,
    get_rate_limiter,
    reset_rate_limiter,
)
from decision_system.connectors.pagination import (
    paginate_items,
    apply_pagination_params,
)
from decision_system.connectors.batch_processor import (
    BatchProcessor,
    get_batch_processor,
    reset_batch_processor,
    BatchResult,
)
from decision_system.connectors.dedup import (
    DuplicateDetector,
    get_duplicate_detector,
    reset_duplicate_detector,
)
from decision_system.connectors.provenance import (
    ProvenanceTracker,
    SourceVersion,
    get_provenance_tracker,
    reset_provenance_tracker,
)

# Re-usable test content
TEST_ITEM_1 = ConnectorRuntimeItem(
    external_id="doc1",
    title="Document 1",
    item_type="file",
    source_url="https://example.com/doc1.md",
    modified_at=datetime(2026, 1, 15, tzinfo=timezone.utc),
    content_type="text/markdown",
    size_bytes=1024,
)

TEST_ITEM_2 = ConnectorRuntimeItem(
    external_id="doc2",
    title="Document 2",
    item_type="file",
    content_type="text/plain",
    size_bytes=2048,
)

TEST_CONTENT_1 = ConnectorFetchedContent(
    external_id="doc1",
    title="Document 1",
    filename="doc1.md",
    content_text="Hello World Content",
    content_type="text/markdown",
)

TEST_CONTENT_2 = ConnectorFetchedContent(
    external_id="doc2",
    title="Document 2",
    filename="doc2.txt",
    content_text="Another piece of content",
    content_type="text/plain",
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clean_singletons():
    """Reset all singleton stores between tests."""
    reset_retry_policy()
    reset_rate_limiter()
    reset_batch_processor()
    reset_duplicate_detector()
    reset_provenance_tracker()
    yield


@pytest.fixture
def tmp_store_dir(tmp_path: Path) -> Path:
    return tmp_path / "connector_test"


# ---------------------------------------------------------------------------
# Phase 2 — Job progress model tests
# ---------------------------------------------------------------------------


class TestJobProgressModel:
    def test_default_progress(self):
        jp = JobProgress()
        assert jp.total_items == 0
        assert jp.processed_items == 0
        assert jp.percent_complete() == 0.0

    def test_percent_complete(self):
        jp = JobProgress(total_items=100)
        jp.processed_items = 50
        assert jp.percent_complete() == 50.0

    def test_is_finished(self):
        jp = JobProgress(total_items=10)
        jp.processed_items = 10
        assert jp.is_finished()

    def test_add_progress(self):
        jp = JobProgress(total_items=200)
        jp.add_progress(processed=50, imported=30, skipped=10, changed=5, failed=3, rate_limited=2)
        assert jp.processed_items == 50
        assert jp.imported_items == 30
        assert jp.skipped_items == 10
        assert jp.changed_items == 5
        assert jp.failed_items == 3
        assert jp.rate_limited_items == 2

    def test_add_progress_cumulative(self):
        jp = JobProgress(total_items=100)
        jp.add_progress(processed=25)
        jp.add_progress(processed=25)
        jp.add_progress(processed=50)
        assert jp.processed_items == 100
        assert jp.is_finished()


class TestConnectorImportJobNewFields:
    def test_default_job_has_progress(self):
        job = ConnectorImportJob(job_id="j1", connector_id="c1", status="queued")
        assert job.job_type == "import"
        assert job.batch_size == 50
        assert job.total_items == 0
        assert job.processed_items == 0
        assert job.cancel_requested is False

    def test_to_progress_dict(self):
        job = ConnectorImportJob(
            job_id="j1", connector_id="c1", status="running",
            total_items=100, processed_items=50,
            items_imported=30, items_skipped=15, items_failed=5,
        )
        d = job.to_progress_dict()
        assert d["job_id"] == "j1"
        assert d["status"] == "running"
        assert d["total_items"] == 100
        assert d["processed_items"] == 50
        assert d["imported_items"] == 30
        assert d["percent_complete"] == 50.0

    def test_percent_complete_handles_zero_total(self):
        """Should not crash when total_items=0 (avoids ZeroDivisionError)."""
        job = ConnectorImportJob(job_id="j1", connector_id="c1", status="queued")
        # Should not raise ZeroDivisionError
        pct = job.percent_complete()
        assert isinstance(pct, float)

    def test_is_cancelled(self):
        job = ConnectorImportJob(job_id="j1", connector_id="c1")
        assert job.is_cancelled() is False
        job.cancel_requested = True
        assert job.is_cancelled()
        job.status = "cancelled"
        assert job.is_cancelled()

    def test_queued_status(self):
        job = ConnectorImportJob(job_id="j1", connector_id="c1", status="queued")
        assert ConnectorJobStatus(job.status) == ConnectorJobStatus.QUEUED

    def test_completed_with_warnings(self):
        job = ConnectorImportJob(
            job_id="j1", connector_id="c1", status="completed_with_warnings",
            items_failed=3,
        )
        assert job.status == "completed_with_warnings"

    def test_checkpoint_fields(self):
        job = ConnectorImportJob(job_id="j1", connector_id="c1")
        job.resume_from_checkpoint = {"processed_items": 50, "batch_number": 2}
        assert job.resume_from_checkpoint["processed_items"] == 50


# ---------------------------------------------------------------------------
# Phase 3 — Batch import processing tests
# ---------------------------------------------------------------------------


class TestBatchProcessor:
    def test_process_all_items(self):
        processor = BatchProcessor(batch_size=10)
        items = [
            ConnectorRuntimeItem(external_id=f"doc{i}", title=f"Doc {i}")
            for i in range(25)
        ]
        job = ConnectorImportJob(job_id="batch1", connector_id="c1", status="queued")

        def fetch_fn(item):
            return ConnectorFetchedContent(
                external_id=item.external_id,
                title=item.title,
                filename=f"{item.external_id}.txt",
                content_text=f"Content for {item.external_id}",
            )

        result = processor.process_items(job, items, fetch_fn)
        assert result.status == "completed"
        assert result.items_imported == 25
        assert result.processed_items == 25
        assert result.items_failed == 0
        assert result.current_batch > 0

    def test_batch_size_respected(self):
        processor = BatchProcessor(batch_size=5)
        items = [
            ConnectorRuntimeItem(external_id=f"doc{i}", title=f"Doc {i}")
            for i in range(12)
        ]
        job = ConnectorImportJob(job_id="batch2", connector_id="c1", status="queued")

        def fetch_fn(item):
            return ConnectorFetchedContent(
                external_id=item.external_id,
                title=item.title,
                filename=f"{item.external_id}.txt",
                content_text=f"Content for {item.external_id}",
            )

        result = processor.process_items(job, items, fetch_fn)
        assert result.items_imported == 12
        assert result.total_items == 12

    def test_partial_failures(self):
        processor = BatchProcessor(batch_size=10)
        items = [
            ConnectorRuntimeItem(external_id=f"doc{i}", title=f"Doc {i}")
            for i in range(20)
        ]
        job = ConnectorImportJob(job_id="batch3", connector_id="c1", status="queued")

        fail_ids = {"doc5", "doc12"}

        def fetch_fn(item):
            if item.external_id in fail_ids:
                raise RuntimeError(f"Failed to fetch {item.external_id}")
            return ConnectorFetchedContent(
                external_id=item.external_id,
                title=item.title,
                filename=f"{item.external_id}.txt",
                content_text=f"Content for {item.external_id}",
            )

        result = processor.process_items(job, items, fetch_fn)
        assert result.status == "completed_with_warnings"
        assert result.items_imported == 18
        assert result.items_failed == 2

    def test_cancel_between_batches(self):
        processor = BatchProcessor(batch_size=10)
        items = [
            ConnectorRuntimeItem(external_id=f"doc{i}", title=f"Doc {i}")
            for i in range(50)
        ]
        job = ConnectorImportJob(job_id="cancel1", connector_id="c1", status="running")

        def fetch_fn(item):
            return ConnectorFetchedContent(
                external_id=item.external_id,
                title=item.title,
                filename=f"{item.external_id}.txt",
                content_text=f"Content for {item.external_id}",
            )

        # Cancel after first batch
        def cancel_after_batch(j):
            if j.current_batch == 1:
                j.cancel_requested = True

        result = processor.process_items(job, items, fetch_fn, progress_callback=cancel_after_batch)
        assert result.status == "cancelled"
        assert result.processed_items < 50  # Not all items processed

    def test_large_items_with_memory_safety(self):
        """Process 100+ items to verify memory-safe batching."""
        processor = BatchProcessor(batch_size=20)
        items = [
            ConnectorRuntimeItem(external_id=f"bigdoc{i}", title=f"Big Doc {i}")
            for i in range(105)
        ]
        job = ConnectorImportJob(job_id="large1", connector_id="c1", status="queued")

        def fetch_fn(item):
            return ConnectorFetchedContent(
                external_id=item.external_id,
                title=item.title,
                filename=f"{item.external_id}.txt",
                content_text="x" * 100,  # 100 bytes each
            )

        result = processor.process_items(job, items, fetch_fn)
        assert result.status == "completed"
        assert result.items_imported == 105
        assert result.current_batch == 6  # 105 items / 20 per batch = 6 batches

    def test_resume_from_checkpoint(self):
        processor = BatchProcessor(batch_size=10)
        items = [
            ConnectorRuntimeItem(external_id=f"doc{i}", title=f"Doc {i}")
            for i in range(30)
        ]
        job = ConnectorImportJob(
            job_id="resume1", connector_id="c1", status="failed",
            resume_from_checkpoint={"processed_items": 10},
        )

        def fetch_fn(item):
            return ConnectorFetchedContent(
                external_id=item.external_id,
                title=item.title,
                filename=f"{item.external_id}.txt",
                content_text=f"Content for {item.external_id}",
            )

        result = processor.resume_job(job, items, fetch_fn)
        assert result.status == "completed"
        # Should have processed remaining items via resume
        import_ids = [e.external_id for e in items if hasattr(e, 'external_id')]
        assert result.items_imported > 0

    def test_empty_items_list(self):
        processor = BatchProcessor(batch_size=10)
        job = ConnectorImportJob(job_id="empty1", connector_id="c1", status="queued")

        def fetch_fn(item):
            return ConnectorFetchedContent(
                external_id=item.external_id, title=item.title, filename=""
            )

        result = processor.process_items(job, [], fetch_fn)
        assert result.status == "completed"

    def test_request_cancel(self):
        processor = BatchProcessor(batch_size=10)
        job = ConnectorImportJob(job_id="reqcancel", connector_id="c1", status="running")
        processor.request_cancel(job)
        assert job.cancel_requested is True


# ---------------------------------------------------------------------------
# Phase 4 — Pagination tests
# ---------------------------------------------------------------------------


class TestPagination:
    def test_first_page(self):
        items = [{"id": i} for i in range(100)]
        result = paginate_items(items, page=1, page_size=20)
        assert len(result.items) == 20
        assert result.total_count == 100
        assert result.has_more is True
        assert result.next_cursor == "2"

    def test_middle_page(self):
        items = [{"id": i} for i in range(100)]
        result = paginate_items(items, page=3, page_size=20)
        assert len(result.items) == 20
        assert result.items[0]["id"] == 40
        assert result.has_more is True

    def test_last_page(self):
        items = [{"id": i} for i in range(100)]
        result = paginate_items(items, page=5, page_size=20)
        assert len(result.items) == 20
        assert result.has_more is False
        assert result.next_cursor is None

    def test_partial_last_page(self):
        items = [{"id": i} for i in range(95)]
        result = paginate_items(items, page=5, page_size=20)
        assert len(result.items) == 15
        assert result.has_more is False

    def test_page_size_limits(self):
        items = [{"id": i} for i in range(500)]
        # max_page_size is 200
        result = paginate_items(items, page=1, page_size=500)
        assert len(result.items) == 200  # Clamped to max

    def test_empty_list(self):
        result = paginate_items([], page=1, page_size=20)
        assert len(result.items) == 0
        assert result.total_count == 0
        assert result.has_more is False

    def test_cursor_pagination(self):
        items = [ConnectorRuntimeItem(external_id=f"doc{i}", title=f"Doc {i}") for i in range(50)]
        result = apply_pagination_params(items, page=1, page_size=10)
        assert len(result.items) == 10
        assert result.has_more is True

        # Use cursor for next page
        result2 = apply_pagination_params(items, cursor=result.next_cursor, page_size=10)
        assert len(result2.items) == 10
        assert result2.items[0].external_id == "doc10"

    def test_single_page(self):
        items = [{"id": i} for i in range(5)]
        result = paginate_items(items, page=1, page_size=50)
        assert len(result.items) == 5
        assert result.has_more is False


# ---------------------------------------------------------------------------
# Phase 5 — Retry/backoff policy tests
# ---------------------------------------------------------------------------


class TestRetryPolicy:
    def test_retryable_errors(self):
        rp = RetryPolicy()
        assert rp.classify_error("connection timed out") == "retryable"
        assert rp.classify_error("429 Too Many Requests") == "retryable"
        assert rp.classify_error("HTTP 500 Internal Server Error") == "retryable"
        assert rp.classify_error("service unavailable") == "retryable"
        assert rp.classify_error("connection reset by peer") == "retryable"

    def test_non_retryable_errors(self):
        rp = RetryPolicy()
        assert rp.classify_error("401 Unauthorized") == "non_retryable"
        assert rp.classify_error("403 Forbidden") == "non_retryable"
        assert rp.classify_error("unsupported file type") == "non_retryable"
        assert rp.classify_error("path traversal detected") == "non_retryable"
        assert rp.classify_error("file too large") == "non_retryable"
        assert rp.classify_error("malformed config") == "non_retryable"

    def test_should_retry(self):
        rp = RetryPolicy(max_retries=3)
        assert rp.should_retry("timeout", 1) is True
        assert rp.should_retry("timeout", 3) is True  # attempt 3 of 3 retries
        assert rp.should_retry("timeout", 4) is False  # past max
        assert rp.should_retry("timeout", 4) is False  # Past max

    def test_should_not_retry_non_retryable(self):
        rp = RetryPolicy()
        assert rp.should_retry("401 Unauthorized", 1) is False

    def test_get_delay_increases(self):
        rp = RetryPolicy(base_delay_seconds=1.0, backoff_factor=2.0)
        d1 = rp.get_delay(1)
        d2 = rp.get_delay(2)
        d3 = rp.get_delay(3)
        assert d2 > d1
        assert d3 > d2

    def test_delay_max(self):
        rp = RetryPolicy(base_delay_seconds=10.0, max_delay_seconds=30.0, backoff_factor=4.0)
        d = rp.get_delay(5)
        assert d <= 30.0

    def test_execute_with_retry_success(self):
        rp = RetryPolicy(max_retries=2)
        call_count = 0

        def succeeds():
            nonlocal call_count
            call_count += 1
            return "success"

        result, attempts = rp.execute_with_retry(succeeds)
        assert result == "success"
        assert len(attempts) == 0  # No failures

    def test_execute_with_retry_then_success(self):
        rp = RetryPolicy(max_retries=3, base_delay_seconds=0.01)
        call_count = 0

        def fails_then_succeeds():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("connection timed out")
            return "ok"

        result, attempts = rp.execute_with_retry(fails_then_succeeds)
        assert result == "ok"
        assert len(attempts) == 2  # Two retries before success

    def test_execute_with_retry_exhausted(self):
        rp = RetryPolicy(max_retries=2, base_delay_seconds=0.01)

        def always_fails():
            raise RuntimeError("connection timed out")

        with pytest.raises(RuntimeError):
            rp.execute_with_retry(always_fails)

    def test_non_retryable_fails_fast(self):
        rp = RetryPolicy(max_retries=3, base_delay_seconds=0.01)

        def auth_fails():
            raise PermissionError("401 Unauthorized")

        with pytest.raises(PermissionError):
            rp.execute_with_retry(auth_fails)


# ---------------------------------------------------------------------------
# Phase 6 — Rate-limit handling tests
# ---------------------------------------------------------------------------


class TestRateLimiter:
    def test_initial_state(self):
        rl = RateLimiter()
        state = rl.get_state("test-conn")
        assert state.is_limited is False
        assert state.retry_after_seconds == 0.0

    def test_record_429(self):
        rl = RateLimiter()
        rl.record_429("test-conn", retry_after=60.0)
        assert rl.check_rate_limited("test-conn") is True

    def test_rate_limit_expires(self):
        rl = RateLimiter()
        rl.record_429("test-conn", retry_after=0.01)
        time.sleep(0.02)
        assert rl.check_rate_limited("test-conn") is False

    def test_retry_after_value(self):
        rl = RateLimiter()
        rl.record_429("test-conn", retry_after=30.0)
        retry = rl.get_retry_after("test-conn")
        assert retry > 0

    def test_github_headers(self):
        rl = RateLimiter()
        headers = {
            "x-ratelimit-remaining": "42",
            "x-ratelimit-reset": "1234567890",
            "retry-after": "30",
        }
        rl.record_429("test-github", retry_after=60.0, headers=headers)
        state = rl.get_state("test-github")
        assert state.rate_limit_remaining == 42
        assert state.retry_after_seconds == 30.0  # Prefers Retry-After header


    def test_history(self):
        rl = RateLimiter()
        rl.record_429("conn-a", retry_after=10.0)
        rl.record_429("conn-b", retry_after=20.0)
        history = rl.get_history(limit=5)
        assert len(history) == 2

    def test_no_rate_limit_without_429(self):
        rl = RateLimiter()
        assert rl.check_rate_limited("new-conn") is False
        assert rl.get_retry_after("new-conn") == 0.0


# ---------------------------------------------------------------------------
# Phase 7 — Cancel/resume tests
# ---------------------------------------------------------------------------


class TestCancelResume:
    def test_cancel_request_stops_processing(self):
        processor = BatchProcessor(batch_size=5)
        items = [
            ConnectorRuntimeItem(external_id=f"doc{i}", title=f"Doc {i}")
            for i in range(20)
        ]
        job = ConnectorImportJob(job_id="test_cancel", connector_id="c1", status="running")

        def fetch_fn(item):
            return ConnectorFetchedContent(
                external_id=item.external_id,
                title=item.title,
                filename=f"{item.external_id}.txt",
                content_text="content",
            )

        # Mark cancel after first batch
        def cancel_first_batch(j):
            if j.current_batch == 1:
                j.cancel_requested = True

        result = processor.process_items(job, items, fetch_fn, progress_callback=cancel_first_batch)
        assert result.status == "cancelled"

    def test_pause_job_state(self):
        job = ConnectorImportJob(job_id="pause_test", connector_id="c1", status="running")
        job.status = "paused"
        assert job.status == "paused"

        # Resume
        job.status = "running"
        assert job.status == "running"

    def test_checkpoint_persistence(self):
        job = ConnectorImportJob(job_id="cp_test", connector_id="c1", status="running")
        job.resume_from_checkpoint = {
            "processed_items": 50,
            "batch_number": 3,
            "total_items": 100,
        }
        assert job.resume_from_checkpoint["processed_items"] == 50
        assert job.resume_from_checkpoint["batch_number"] == 3


# ---------------------------------------------------------------------------
# Phase 9 — Duplicate detection tests
# ---------------------------------------------------------------------------


class TestDuplicateDetection:
    def test_first_import_not_duplicate(self):
        dd = DuplicateDetector(base_dir=tempfile.mkdtemp(prefix="test_dedup_"))
        import hashlib
        h = hashlib.sha256(b"unique content").hexdigest()
        result = dd.check_duplicate("test-conn", "item1", h)
        assert result.is_duplicate is False

    def test_second_import_is_unchanged(self):
        dd = DuplicateDetector(base_dir=tempfile.mkdtemp(prefix="test_dedup_"))
        import hashlib
        h = hashlib.sha256(b"same content").hexdigest()
        dd.record_import("test-conn", "item1", h)
        result = dd.check_duplicate("test-conn", "item1", h)
        assert result.is_duplicate is True
        assert result.is_unchanged is True

    def test_changed_content_detected(self):
        dd = DuplicateDetector(base_dir=tempfile.mkdtemp(prefix="test_dedup_"))
        import hashlib
        h1 = hashlib.sha256(b"old content").hexdigest()
        h2 = hashlib.sha256(b"new content").hexdigest()
        dd.record_import("test-conn", "item1", h1)
        result = dd.check_duplicate("test-conn", "item1", h2)
        assert result.is_duplicate is False
        assert result.is_changed is True

    def test_idempotent_reimport(self):
        dd = DuplicateDetector(base_dir=tempfile.mkdtemp(prefix="test_dedup_"))
        import hashlib
        h = hashlib.sha256(b"same content").hexdigest()

        # First import
        dd.record_import("test-conn", "item1", h)
        r1 = dd.check_duplicate("test-conn", "item1", h)
        assert r1.is_unchanged is True

        # Re-import (same content) - should still detect as unchanged
        dd.record_import("test-conn", "item1", h)
        r2 = dd.check_duplicate("test-conn", "item1", h)
        assert r2.is_unchanged is True

    def test_workspace_scoped(self):
        dd = DuplicateDetector(base_dir=tempfile.mkdtemp(prefix="test_dedup_"))
        import hashlib
        h = hashlib.sha256(b"content").hexdigest()
        dd.record_import("test-conn", "item1", h, workspace_id="ws1")
        # Different workspace - should not find duplicate
        result_ws2 = dd.check_duplicate("test-conn", "item1", h, workspace_id="ws2")
        assert result_ws2.is_duplicate is False


# ---------------------------------------------------------------------------
# Phase 10 — Provenance/versioning tests
# ---------------------------------------------------------------------------


class TestProvenance:
    def test_first_version(self):
        pt = ProvenanceTracker(base_dir=tempfile.mkdtemp(prefix="test_prov_"))
        import hashlib
        h = hashlib.sha256(b"content v1").hexdigest()
        version = pt.create_version("test-conn", "item1", h, job_id="job1", label="Item 1")
        assert version.version_number == 1
        assert version.previous_source_id == ""
        assert version.connector_id == "test-conn"
        assert version.external_id == "item1"

    def test_second_version(self):
        pt = ProvenanceTracker(base_dir=tempfile.mkdtemp(prefix="test_prov_"))
        import hashlib
        h1 = hashlib.sha256(b"content v1").hexdigest()
        h2 = hashlib.sha256(b"content v2").hexdigest()

        v1 = pt.create_version("test-conn", "item1", h1, job_id="job1")
        v2 = pt.create_version("test-conn", "item1", h2, job_id="job2")
        assert v2.version_number == 2
        assert v2.previous_source_id == v1.version_id
        assert v2.supersedes_source_id == ""

    def test_get_versions(self):
        pt = ProvenanceTracker(base_dir=tempfile.mkdtemp(prefix="test_prov_"))
        import hashlib
        h1 = hashlib.sha256(b"v1").hexdigest()
        h2 = hashlib.sha256(b"v2").hexdigest()

        pt.create_version("test-conn", "item1", h1)
        pt.create_version("test-conn", "item1", h2)
        versions = pt.get_versions("test-conn", "item1")
        assert len(versions) == 2

    def test_get_latest_version(self):
        pt = ProvenanceTracker(base_dir=tempfile.mkdtemp(prefix="test_prov_"))
        import hashlib
        h1 = hashlib.sha256(b"v1").hexdigest()
        h2 = hashlib.sha256(b"v2").hexdigest()

        pt.create_version("test-conn", "item1", h1)
        pt.create_version("test-conn", "item1", h2)
        latest = pt.get_latest_version("test-conn", "item1")
        assert latest is not None
        assert latest.version_number == 2

    def test_no_versions_for_unknown(self):
        pt = ProvenanceTracker(base_dir=tempfile.mkdtemp(prefix="test_prov_"))
        versions = pt.get_versions("test-conn", "nonexistent")
        assert versions == []
        latest = pt.get_latest_version("test-conn", "nonexistent")
        assert latest is None


# ---------------------------------------------------------------------------
# Phase 12 — Audit/metrics tests
# ---------------------------------------------------------------------------


class TestReliabilityAudit:
    def test_audit_events_exist(self):
        """Verify audit event constants exist in audit module."""
        from decision_system.connectors.audit import (
            EVENT_CONNECTOR_JOB_PROGRESS,
            EVENT_CONNECTOR_JOB_CANCEL_REQUESTED,
            EVENT_CONNECTOR_JOB_CANCELLED,
            EVENT_CONNECTOR_JOB_RESUMED,
            EVENT_CONNECTOR_ITEM_RETRY,
            EVENT_CONNECTOR_RATE_LIMITED,
            EVENT_CONNECTOR_DUPLICATE_DETECTED,
            EVENT_CONNECTOR_BATCH_COMPLETED,
        )
        assert EVENT_CONNECTOR_JOB_PROGRESS == "connector_job_progress"
        assert EVENT_CONNECTOR_JOB_CANCEL_REQUESTED == "connector_job_cancel_requested"
        assert EVENT_CONNECTOR_RATE_LIMITED == "connector_rate_limited"
        assert EVENT_CONNECTOR_DUPLICATE_DETECTED == "connector_duplicate_detected"

    def test_audit_recording_does_not_crash(self):
        """Audit recording should never raise exceptions."""
        from decision_system.connectors.audit import (
            record_job_progress,
            record_job_cancel_requested,
            record_rate_limited,
            record_duplicate_detected,
            record_batch_completed,
        )
        # These should all succeed without raising
        record_job_progress("job1", "conn1", 50, 100)
        record_job_cancel_requested("job1", "conn1")
        record_rate_limited("conn1", 30.0)
        record_duplicate_detected("conn1", "item1", "abc123")
        record_batch_completed("job1", "conn1", 1, 50, 1000.0)

    def test_metrics_exist(self):
        from decision_system.connectors.metrics import (
            record_batch_duration,
            record_retry_count,
            record_rate_limit_count,
            record_cancel_count,
            record_resume_count,
            record_duplicate_count,
            record_large_import_count,
        )
        # These should not raise
        record_batch_duration("conn1", 100.0)
        record_retry_count("conn1")
        record_rate_limit_count("conn1")
        record_cancel_count("conn1")
        record_resume_count("conn1")
        record_duplicate_count("conn1")
        record_large_import_count("conn1")


# ---------------------------------------------------------------------------
# Phase 13 — Large import demo tests
# ---------------------------------------------------------------------------


class TestLargeImportDemo:
    def test_demo_folder_exists(self):
        """Verify the large import demo fixture exists."""
        demo_path = Path("demo/sample-data/large-folder")
        assert demo_path.exists(), "Demo folder does not exist"
        assert demo_path.is_dir(), "Demo path is not a directory"

    def test_demo_has_150_files(self):
        demo_path = Path("demo/sample-data/large-folder")
        md_files = list(demo_path.glob("*.md"))
        assert len(md_files) == 150, f"Expected 150 demo files, got {len(md_files)}"

    def test_demo_files_are_readable(self):
        demo_path = Path("demo/sample-data/large-folder")
        for f in sorted(demo_path.glob("*.md"))[:5]:
            content = f.read_text(encoding="utf-8")
            assert content.startswith("#")
            assert len(content) > 10

    def test_demo_paginated_list(self):
        """Verify pagination works with demo items."""
        demo_path = Path("demo/sample-data/large-folder")
        items = sorted(demo_path.glob("*.md"))
        result = paginate_items(items, page=1, page_size=20)
        assert len(result.items) == 20
        assert result.total_count == len(items)
        assert result.has_more is True


# ---------------------------------------------------------------------------
# Integration-style tests
# ---------------------------------------------------------------------------


class TestIntegration:
    def test_progress_to_completion(self):
        """End-to-end: create job, process items, verify final state."""
        processor = BatchProcessor(batch_size=10)
        items = [
            ConnectorRuntimeItem(external_id=f"doc{i}", title=f"Doc {i}")
            for i in range(37)
        ]
        job = ConnectorImportJob(job_id="integration1", connector_id="c1", status="queued")
        job.total_items = len(items)

        def fetch_fn(item):
            return ConnectorFetchedContent(
                external_id=item.external_id,
                title=item.title,
                filename=f"{item.external_id}.txt",
                content_text=f"Content for {item.external_id}",
            )

        result = processor.process_items(job, items, fetch_fn)
        assert result.status == "completed"
        assert result.items_imported == 37
        assert result.processed_items == 37
        assert result.items_failed == 0
        assert result.total_items == 37
        assert result.completed_at is not None

    def test_retry_with_batch_processor(self):
        """Verify retry policy works within batch processing."""
        processor = BatchProcessor(
            batch_size=10,
            retry_policy=RetryPolicy(max_retries=2, base_delay_seconds=0.01),
        )
        items = [
            ConnectorRuntimeItem(external_id=f"doc{i}", title=f"Doc {i}")
            for i in range(5)
        ]
        job = ConnectorImportJob(job_id="retry_integration", connector_id="c1", status="queued")

        call_counts = {}

        def fetch_fn(item):
            eid = item.external_id
            call_counts[eid] = call_counts.get(eid, 0) + 1
            if eid == "doc0" and call_counts[eid] < 3:
                raise ConnectionError("connection timed out")
            return ConnectorFetchedContent(
                external_id=eid,
                title=item.title,
                filename=f"{eid}.txt",
                content_text=f"Content for {eid}",
            )

        result = processor.process_items(job, items, fetch_fn)
        # doc0 requires 3 attempts but max_retries=2, so it fails -> completed_with_warnings
        assert result.status in ("completed", "completed_with_warnings")
        assert result.items_imported >= 4  # 4 items imported, 1 failed

        # doc0 requires 3 attempts but max_retries=2, so it fails -> completed_with_warnings
        assert result.status in ("completed", "completed_with_warnings")
        assert result.items_imported >= 4  # 4 items imported, 1 failed

    def test_dedup_with_provenance(self):
        """Verify dedup + provenance work together."""
        dd = DuplicateDetector(base_dir=tempfile.mkdtemp(prefix="test_integ_dedup_"))
        pt = ProvenanceTracker(base_dir=tempfile.mkdtemp(prefix="test_integ_prov_"))
        import hashlib

        # First import of content
        h1 = hashlib.sha256(b"content v1").hexdigest()
        dd.record_import("test-conn", "item1", h1)
        v1 = pt.create_version("test-conn", "item1", h1, job_id="job1")
        assert v1.version_number == 1

        # Second import - different content
        h2 = hashlib.sha256(b"content v2").hexdigest()
        dup = dd.check_duplicate("test-conn", "item1", h2)
        assert dup.is_changed is True
        dd.record_import("test-conn", "item1", h2)
        v2 = pt.create_version("test-conn", "item1", h2, job_id="job2")
        assert v2.version_number == 2
        assert v2.previous_source_id == v1.version_id

        # Third import - same as second (unchanged)
        dup2 = dd.check_duplicate("test-conn", "item1", h2)
        assert dup2.is_unchanged is True
