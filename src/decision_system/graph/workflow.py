"""LangGraph workflow definition for the bounded decision pipeline.

The v0.1 graph is deliberately linear and terminating. There are no back edges
or agent-to-agent chat nodes, which keeps cost, state, and failure modes
predictable while the evidence and claim-ledger architecture is still young.
"""

from langgraph.graph import END, START, StateGraph

from decision_system.graph.nodes import (
    claim_extraction_node,
    report_writer_node,
    retrieve_evidence_node,
    risk_analyst_node,
    technical_analyst_node,
    verifier_node,
)
from decision_system.graph.state import WorkflowState


def build_workflow():
    """Compile the v0.1 decision workflow.

    Returns:
        A compiled LangGraph runnable that accepts `WorkflowState` input and
        returns final state containing a `DecisionReport`.
    """

    builder = StateGraph(WorkflowState)
    builder.add_node("retrieve_evidence", retrieve_evidence_node)
    builder.add_node("technical_analyst", technical_analyst_node)
    builder.add_node("risk_analyst", risk_analyst_node)
    builder.add_node("claim_extraction", claim_extraction_node)
    builder.add_node("verifier", verifier_node)
    builder.add_node("report_writer", report_writer_node)
    # Safety constraint: every edge moves forward exactly once; no loops or
    # free-form agent conversations are allowed in v0.1.
    builder.add_edge(START, "retrieve_evidence")
    builder.add_edge("retrieve_evidence", "technical_analyst")
    builder.add_edge("technical_analyst", "risk_analyst")
    builder.add_edge("risk_analyst", "claim_extraction")
    builder.add_edge("claim_extraction", "verifier")
    builder.add_edge("verifier", "report_writer")
    builder.add_edge("report_writer", END)
    return builder.compile()
