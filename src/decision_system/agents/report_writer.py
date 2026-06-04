from decision_system.models import Claim, DecisionReport
from decision_system.reports.renderer import render_decision_report


def write_report(question: str, run_id: str, claims: list[Claim]) -> DecisionReport:
    return render_decision_report(question, run_id, claims)
