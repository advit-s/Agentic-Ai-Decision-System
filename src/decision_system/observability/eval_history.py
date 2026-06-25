"""Evaluation history recorder and inspector."""

from __future__ import annotations

from typing import Any, Optional

from .models import EvalRunRecord
from .store import load_eval_runs, save_eval_run


class EvalHistory:
    """Persist and inspect evaluation run records."""

    def __init__(self, root: Optional[str] = None) -> None:
        self._root = root
        self._runs_by_id: dict[str, EvalRunRecord] = {}
        self._load_cached()

    def _load_cached(self) -> None:
        try:
            for run in load_eval_runs(self._root):
                self._runs_by_id[run.run_id] = run
        except Exception:
            pass

    def record_run(self, record: EvalRunRecord) -> str:
        save_eval_run(record, self._root)
        self._runs_by_id[record.run_id] = record
        return record.run_id

    def get_run(self, run_id: str) -> Optional[EvalRunRecord]:
        return self._runs_by_id.get(run_id)

    def get_all_runs(self) -> list[EvalRunRecord]:
        return sorted(self._runs_by_id.values(), key=lambda r: r.started_at, reverse=True)

    def get_runs_by_type(self, eval_type: str) -> list[EvalRunRecord]:
        return [r for r in self.get_all_runs() if r.eval_type == eval_type]

    def get_summary(self) -> dict[str, Any]:
        runs = self.get_all_runs()
        total = len(runs)
        passed = sum(1 for r in runs if r.status.value == "passed")
        failed = sum(1 for r in runs if r.status.value == "failed")
        skipped = sum(1 for r in runs if r.status.value == "skipped")
        error = sum(1 for r in runs if r.status.value == "error")
        total_cases = sum(r.total_cases for r in runs)
        duration = sum(r.duration_seconds for r in runs)
        return {
            "total_runs": total,
            "passed_runs": passed,
            "failed_runs": failed,
            "skipped_runs": skipped,
            "error_runs": error,
            "total_cases": total_cases,
            "cumulative_duration_seconds": duration,
        }
