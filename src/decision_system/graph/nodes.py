"""LangGraph node implementations for the v0.1 decision workflow.

Each node accepts shared `WorkflowState` and returns a partial state update.
This keeps retrieval, analysis, verification, and report writing as separate
auditable steps.
"""

from decision_system.agents.risk_analyst import run_risk_analysis
from decision_system.agents.technical_analyst import run_technical_analysis
from decision_system.config import load_settings
from decision_system.graph.state import WorkflowState
from decision_system.ledger.claim_ledger import ClaimLedger
from decision_system.ledger.verifier import verify_claims
from decision_system.llm.factory import get_provider
from decision_system.llm.provider import LLMProvider
from decision_system.reports.renderer import render_decision_report


def _provider_for_state(state: WorkflowState) -> LLMProvider:
    return get_provider(provider_name=state.get("provider"))


def retrieve_evidence_node(state: WorkflowState) -> dict:
    """Retrieve evidence unless prior evidence was injected by a test.

    Inputs:
        Workflow state with `question`, optional `top_k`, and optional
        `retrieved_evidence`.

    Returns:
        Partial state containing `retrieved_evidence`.

    Side effects:
        Reads the local Chroma store when evidence is not already present.
    """

    if state.get("retrieved_evidence"):
        return {"retrieved_evidence": state["retrieved_evidence"]}

    # Delay the Chroma import so graph unit tests can run without touching the
    # vector store when they inject evidence directly.
    from decision_system.rag.retriever import retrieve_evidence

    settings = load_settings()
    evidence = retrieve_evidence(
        state["question"],
        store_dir=settings.store_dir,
        collection_name=settings.collection_name,
        top_k=state.get("top_k", 6),
    )
    return {"retrieved_evidence": evidence}


def technical_analyst_node(state: WorkflowState) -> dict:
    """Create the bounded technical analysis memo."""

    provider = _provider_for_state(state)
    memo = run_technical_analysis(
        state["question"],
        state.get("retrieved_evidence", []),
        provider=provider,
    )
    return {"technical_memo": memo}


def risk_analyst_node(state: WorkflowState) -> dict:
    """Create the bounded risk/red-team memo."""

    provider = _provider_for_state(state)
    memo = run_risk_analysis(
        state["question"],
        state.get("retrieved_evidence", []),
        state["technical_memo"],
        provider=provider,
    )
    return {"risk_memo": memo}


def claim_extraction_node(state: WorkflowState) -> dict:
    """Convert agent memo claims into ledger-ready `Claim` records."""

    provider = _provider_for_state(state)
    claims = provider.extract_claims(
        state["run_id"],
        [state["technical_memo"], state["risk_memo"]],
    )
    ledger = ClaimLedger()
    ledger.add_claims(claims)
    return {"claims": ledger.all_claims()}


def verifier_node(state: WorkflowState) -> dict:
    """Mark claims as verified, unsupported, or contradicted."""

    claims, results = verify_claims(
        state.get("claims", []),
        state.get("retrieved_evidence", []),
    )
    return {"claims": claims, "verification_results": results}


def report_writer_node(state: WorkflowState) -> dict:
    """Render the final report from verified ledger state only."""

    report = render_decision_report(
        state["question"],
        state["run_id"],
        state.get("claims", []),
    )
    return {"final_report": report}
