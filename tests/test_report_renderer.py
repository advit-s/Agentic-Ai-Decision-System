from decision_system.models import Claim
from decision_system.reports.renderer import render_decision_report


def test_report_includes_required_sections_and_ledger_claims():
    claims = [
        Claim(
            claim_id="claim-1",
            run_id="run-1",
            source_agent="technical_analyst",
            claim_text="Billing migration requires rollback planning.",
            claim_type="technical",
            status="verified",
            evidence_ids=["doc-a:chunk-0001"],
            confidence="high",
            verification_notes="Cited evidence supports the claim.",
        ),
        Claim(
            claim_id="claim-2",
            run_id="run-1",
            source_agent="risk_analyst",
            claim_text="Migration can happen without downtime.",
            claim_type="risk",
            status="contradicted",
            contradicting_evidence_ids=["doc-a:chunk-0002"],
            confidence="high",
            verification_notes="Contradiction marker found.",
        ),
    ]

    report = render_decision_report("Should we migrate billing?", "run-1", claims)

    assert "## Recommendation" in report.markdown
    assert "## Evidence Citations" in report.markdown
    assert "doc-a:chunk-0001" in report.markdown
    assert report.contradictions[0].claim_id == "claim-2"
    assert report.human_review_required
