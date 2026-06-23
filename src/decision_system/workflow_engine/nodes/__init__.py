"""Node definitions — base classes, registry, and built-in node types."""

from decision_system.workflow_engine.nodes.registry import NodeRegistry

# Built-in imports
from decision_system.workflow_engine.nodes.builtin import (
    ManualTriggerNode, InputTextNode,
    CronTriggerNode, WebhookTriggerNode, FileWatchTriggerNode,
    FilterNode, MergeNode, CodeNode,
    RetrieveNode, TechAnalystNode, RiskAnalystNode,
    ExtractClaimsNode, VerifyClaimsNode, WriteReportNode,
    ExtractGraphNode, ProfileDataNode, MapOntologyNode,
    DetectPatternsNode, WarRoomNode,
    EvidenceSearchNode,
    ClaimVerifierNode,
    ContradictionScanNode,
    VerificationSummaryNode,
)
from decision_system.workflow_engine.nodes.specialist import (
    ResearcherNode, CriticNode, SynthesizerNode, DataAnalystNode,
    ReviewGateNode, PlannerNode, AuditorNode, ComplianceCheckerNode,
    CodeRunnerNode,
)


def create_default_registry() -> NodeRegistry:
    """Create a registry pre-populated with all built-in node types."""
    registry = NodeRegistry()
    for node_cls in _ALL_BUILTIN_NODES:
        registry.register(node_cls)
    return registry


_ALL_BUILTIN_NODES = [
    ManualTriggerNode, InputTextNode,
    CronTriggerNode, WebhookTriggerNode, FileWatchTriggerNode,
    FilterNode, MergeNode, CodeNode,
    RetrieveNode, TechAnalystNode, RiskAnalystNode,
    ExtractClaimsNode, VerifyClaimsNode, WriteReportNode,
    ExtractGraphNode, ProfileDataNode, MapOntologyNode,
    DetectPatternsNode, WarRoomNode,
    EvidenceSearchNode,
    ClaimVerifierNode, ContradictionScanNode, VerificationSummaryNode,
    ResearcherNode, CriticNode, SynthesizerNode, DataAnalystNode,
    ReviewGateNode,
    PlannerNode, AuditorNode, ComplianceCheckerNode, CodeRunnerNode,
]

__all__ = [
    "NodeRegistry", "create_default_registry",
    "ManualTriggerNode", "InputTextNode",
    "CronTriggerNode", "WebhookTriggerNode", "FileWatchTriggerNode",
    "FilterNode", "MergeNode", "CodeNode",
    "RetrieveNode", "TechAnalystNode", "RiskAnalystNode",
    "ExtractClaimsNode", "VerifyClaimsNode", "WriteReportNode",
    "ExtractGraphNode", "ProfileDataNode", "MapOntologyNode",
    "DetectPatternsNode", "WarRoomNode",
    "EvidenceSearchNode",
    "ResearcherNode", "CriticNode", "SynthesizerNode", "DataAnalystNode",
    "ReviewGateNode",
    "PlannerNode", "AuditorNode", "ComplianceCheckerNode", "CodeRunnerNode",
]
