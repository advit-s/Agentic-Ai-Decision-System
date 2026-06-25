"""Node registry — discovers, registers, and instantiates node types."""

from __future__ import annotations

from typing import Any

from decision_system.workflow_engine.models import (
    NodeTypeInfo,
    WorkflowNode,
)


class NodeRegistry:
    """Thread-safe registry of all known node types.

    Node types are registered by calling register() with a WorkflowNode
    subclass. The registry can then look up types by name, list all types,
    and instantiate nodes from NodeConfig references.
    """

    def __init__(self) -> None:
        self._types: dict[str, type[WorkflowNode]] = {}

    @staticmethod
    def _get_field_default(node_cls: type[WorkflowNode], field_name: str) -> Any:
        """Get the default value of a Pydantic model field.

        Pydantic v2 does not expose field defaults as class-level attributes,
        so we use model_fields to look them up.
        """
        field_info = node_cls.model_fields.get(field_name)
        if field_info is None:
            return None
        # For fields with a default value (not required), return the default
        if not field_info.is_required():
            return field_info.default
        return None

    def register(self, node_cls: type[WorkflowNode]) -> None:
        """Register a node type. Raises ValueError on duplicate."""
        node_type = self._get_field_default(node_cls, "type")
        if not node_type:
            raise ValueError(f"Node class {node_cls.__name__} must have a 'type' attribute")
        if node_type in self._types:
            raise ValueError(f"Node type '{node_type}' is already registered")
        self._types[node_type] = node_cls

    def get(self, node_type: str) -> type[WorkflowNode]:
        """Get a registered node class by type string. Raises KeyError if not found."""
        if node_type not in self._types:
            raise KeyError(f"Node type '{node_type}' not found in registry")
        return self._types[node_type]

    def list_types(self) -> list[NodeTypeInfo]:
        """List metadata for all registered node types."""
        result: list[NodeTypeInfo] = []
        for node_type, node_cls in sorted(self._types.items()):
            try:
                config_schema = node_cls.get_config_schema()
                input_schema = node_cls.get_input_schema()
                output_schema = node_cls.get_output_schema()
            except Exception:
                config_schema = {}
                input_schema = {}
                output_schema = {}
            result.append(
                NodeTypeInfo(
                    type=node_type,
                    label=self._get_field_default(node_cls, "label") or node_type,
                    description=getattr(node_cls, "__doc__", "") or "",
                    config_schema=config_schema,
                    input_schema=input_schema,
                    output_schema=output_schema,
                )
            )
        return result

    def instantiate(self, node_type: str, **overrides: Any) -> WorkflowNode:
        """Create a node instance from a type string and overrides."""
        node_cls = self.get(node_type)
        return node_cls(**overrides)

    def __contains__(self, node_type: str) -> bool:
        return node_type in self._types
