"""Node registry — discovers, registers, and instantiates node types."""

from __future__ import annotations

from typing import Any

from decision_system.workflow_engine.models import (
    WorkflowNode, NodeTypeInfo, NodeConfig,
)


class NodeRegistry:
    """Thread-safe registry of all known node types.

    Node types are registered by calling register() with a WorkflowNode
    subclass. The registry can then look up types by name, list all types,
    and instantiate nodes from NodeConfig references.
    """

    def __init__(self) -> None:
        self._types: dict[str, type[WorkflowNode]] = {}

    def register(self, node_cls: type[WorkflowNode]) -> None:
        """Register a node type. Raises ValueError on duplicate."""
        node_type = self._get_node_type(node_cls)
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
            result.append(NodeTypeInfo(
                type=node_type,
                label=self._get_label(node_cls) or node_type,
                description=getattr(node_cls, "__doc__", "") or "",
                config_schema=config_schema,
                input_schema=input_schema,
                output_schema=output_schema,
            ))
        return result

    def instantiate(self, node_type: str, **overrides: Any) -> WorkflowNode:
        """Create a node instance from a type string and overrides."""
        node_cls = self.get(node_type)
        return node_cls(**overrides)

    @staticmethod
    def _get_node_type(node_cls: type[WorkflowNode]) -> str | None:
        """Get the type field value from a WorkflowNode subclass.

        Uses model_fields to handle Pydantic V2 ABC field storage.
        """
        fields = getattr(node_cls, "model_fields", {})
        type_field = fields.get("type")
        if type_field is not None:
            return type_field.default
        return getattr(node_cls, "type", None)

    @staticmethod
    def _get_label(node_cls: type[WorkflowNode]) -> str:
        """Get the label field value from a WorkflowNode subclass."""
        fields = getattr(node_cls, "model_fields", {})
        label_field = fields.get("label")
        if label_field is not None and label_field.default:
            return label_field.default
        return getattr(node_cls, "label", "") or ""

    def __contains__(self, node_type: str) -> bool:
        return node_type in self._types
