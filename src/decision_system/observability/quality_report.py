"""Generate quality reports from evaluation history."""

from __future__ import annotations

from typing import Any, Optional

from .models import QualityDimension, QualityReport
from .store import load_eval_runs, save_quality_report


def generate_quality_report(
    target_type: str = "eval_run",
    target_id: Optional[str] = None,
    root: Optional[str] = None,
) -> QualityReport:
    runs = load_eval_runs(root)
    if not runs:
        return QualityReport(
            target_type=target_type,
            target_id=target_id or "none",
            overall_score=0.0,
            overall_status="pass",
            dimension_scores={},
            recommendations=["No evaluation runs found. Run evaluations first."],
        )
    latest = runs[0]
    total = latest.total_cases
    if total == 0:
        total_score = 0.0
    else:
        pass_rate = latest.passed_cases / total if total else 0.0
        total_score = pass_rate

    dimension_scores: dict[QualityDimension, float] = {}
    for d in QualityDimension:
        dimension_scores[d] = total_score

    status = "pass" if total_score >= 0.8 else "warn" if total_score >= 0.5 else "fail"

    report = QualityReport(
        target_type=target_type,
        target_id=latest.run_id,
        overall_score=total_score,
        overall_status=status,
        dimension_scores=dimension_scores,
    )
    save_quality_report(report, root)
    return report


def quality_report_summary_json(report: QualityReport) -> dict[str, Any]:
    return {
        "report_id": report.report_id,
        "target_type": report.target_type,
        "target_id": report.target_id,
        "overall_score": report.overall_score,
        "overall_status": report.overall_status,
        "dimension_scores": {d.value: s for d, s in report.dimension_scores.items()},
        "recommendations": report.recommendations,
        "created_at": report.created_at.isoformat() if report.created_at else None,
    }
