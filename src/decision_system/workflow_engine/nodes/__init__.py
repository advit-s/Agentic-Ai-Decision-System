"""Node definitions — base classes, registry, and built-in node types."""

from decision_system.workflow_engine.nodes.registry import NodeRegistry

# Built-in imports
from decision_system.workflow_engine.nodes.builtin import (
    ManualTriggerNode, InputTextNode,
    FilterNode, MergeNode, CodeNode,
    RetrieveNode, TechAnalystNode, RiskAnalystNode,
    ExtractClaimsNode, VerifyClaimsNode, WriteReportNode,
    ExtractGraphNode, ProfileDataNode, MapOntologyNode,
    DetectPatternsNode, WarRoomNode,
)

def create_default_registry() -> NodeRegistry:
    """Create a registry pre-populated with all built-in node types."""
    registry = NodeRegistry()
    for node_cls in _ALL_BUILTIN_NODES:
        registry.register(node_cls)
    return registry


_ALL_BUILTIN_NODES = [
    ManualTriggerNode, InputTextNode,
    FilterNode, MergeNode, CodeNode,
    RetrieveNode, TechAnalystNode, RiskAnalystNode,
    ExtractClaimsNode, VerifyClaimsNode, WriteReportNode,
    ExtractGraphNode, ProfileDataNode, MapOntologyNode,
    DetectPatternsNode, WarRoomNode,
]

__all__ = [
    "NodeRegistry", "create_default_registry",
    "ManualTriggerNode", "InputTextNode",
    "FilterNode", "MergeNode", "CodeNode",
    "RetrieveNode", "TechAnalystNode", "RiskAnalystNode",
    "ExtractClaimsNode", "VerifyClaimsNode", "WriteReportNode",
    "ExtractGraphNode", "ProfileDataNode", "MapOntologyNode",
    "DetectPatternsNode", "WarRoomNode",
]
