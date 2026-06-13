"""Specialist agent node types — AI-powered bounded agents for the workflow builder.

Each node uses the Phase 5 provider system to call real LLMs, with
deterministic fake fallback when no provider is configured.
"""

from decision_system.workflow_engine.nodes.specialist.researcher import ResearcherNode
# from decision_system.workflow_engine.nodes.specialist.critic import CriticNode
# from decision_system.workflow_engine.nodes.specialist.synthesizer import SynthesizerNode

__all__ = [
    "ResearcherNode",
    # "CriticNode",
    # "SynthesizerNode",
]
