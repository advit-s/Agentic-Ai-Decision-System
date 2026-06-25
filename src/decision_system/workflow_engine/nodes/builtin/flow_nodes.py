"""Built-in flow control node types."""

from __future__ import annotations

from decision_system.workflow_engine.models import (
    ExecutionContext,
    WorkflowNode,
)


class FilterNode(WorkflowNode):
    """Conditionally passes data through based on a filter expression.
    If the condition evaluates to False, the node outputs the original
    inputs unchanged (pass-through).
    """

    type: str = "decision_system.filter"
    label: str = "Filter"

    async def execute(self, inputs: dict, ctx: ExecutionContext) -> dict:
        field = self.config.get("field", "")
        operator = self.config.get("operator", "exists")
        value = self.config.get("value", None)

        target = inputs.get(field) if field else None
        passed = True  # pass through by default

        if field and target is not None:
            if operator == "exists":
                passed = True
            elif operator == "equals":
                passed = target == value
            elif operator == "not_equals":
                passed = target != value
            elif operator == "greater_than":
                try:
                    passed = float(target) > float(value)  # type: ignore[arg-type]
                except (TypeError, ValueError):
                    passed = False
            elif operator == "less_than":
                try:
                    passed = float(target) < float(value)  # type: ignore[arg-type]
                except (TypeError, ValueError):
                    passed = False
        elif field and target is None:
            passed = False

        return {
            "passed": passed,
            "filtered": not passed,
            **inputs,
        }

    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "field": {
                    "type": "string",
                    "title": "Field",
                    "description": "Input field to check",
                },
                "operator": {
                    "type": "string",
                    "title": "Operator",
                    "enum": [
                        "exists",
                        "equals",
                        "not_equals",
                        "greater_than",
                        "less_than",
                    ],
                    "default": "exists",
                },
                "value": {
                    "title": "Value",
                    "description": "Value to compare against",
                },
            },
        }

    @classmethod
    def get_input_schema(cls) -> dict:
        return {"type": "object", "properties": {}}

    @classmethod
    def get_output_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "passed": {"type": "boolean"},
                "filtered": {"type": "boolean"},
            },
        }


class MergeNode(WorkflowNode):
    """Merges multiple upstream inputs into a single output.
    Merge strategies:
    - merge: shallow merge of all input dicts (later keys overwrite earlier)
    - concat: concatenate lists found at the specified field name
    """

    type: str = "decision_system.merge"
    label: str = "Merge"

    async def execute(self, inputs: dict, ctx: ExecutionContext) -> dict:
        strategy = self.config.get("strategy", "merge")
        input_field = self.config.get("input_field", "default")

        if strategy == "merge":
            return {**inputs}
        elif strategy == "concat":
            items = []
            for key, value in inputs.items():
                if isinstance(value, list):
                    items.extend(value)
                elif isinstance(value, dict):
                    inner = value.get(input_field, [])
                    if isinstance(inner, list):
                        items.extend(inner)
            return {"items": items, "count": len(items)}
        return inputs

    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "strategy": {
                    "type": "string",
                    "title": "Merge Strategy",
                    "enum": ["merge", "concat"],
                    "default": "merge",
                },
                "input_field": {
                    "type": "string",
                    "title": "Input Field",
                    "description": "Field name for concat strategy",
                    "default": "default",
                },
            },
        }

    @classmethod
    def get_input_schema(cls) -> dict:
        return {"type": "object", "properties": {}}

    @classmethod
    def get_output_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "items": {"type": "array"},
                "count": {"type": "integer"},
            },
        }


class CodeNode(WorkflowNode):
    """Executes a user-provided Python code snippet.
    The code receives `inputs` dict and `ctx` (ExecutionContext) as locals.
    Must set `output` variable with the result dict.

    SAFETY: This node is DISABLED by default. To enable it, set the
    environment variable DECISION_SYSTEM_ENABLE_UNSAFE_CODE_NODE=true.
    When enabled, the node uses Python's exec() with builtins available,
    which can execute arbitrary code. Use with extreme caution.
    """

    type: str = "decision_system.code"
    label: str = "Code"

    async def execute(self, inputs: dict, ctx: ExecutionContext) -> dict:
        import os

        enabled = os.environ.get("DECISION_SYSTEM_ENABLE_UNSAFE_CODE_NODE", "false").lower() in (
            "1",
            "true",
            "yes",
        )
        if not enabled:
            raise RuntimeError(
                "CodeNode is disabled by default for safety. "
                "Set DECISION_SYSTEM_ENABLE_UNSAFE_CODE_NODE=true to enable. "
                "See docs/SECURITY_MODEL.md for details."
            )

        source = self.config.get("source", "")
        if not source.strip():
            return inputs

        # Prepare safe locals
        local_vars: dict = {"inputs": inputs, "ctx": ctx, "output": {}}
        exec_globals: dict = {"__builtins__": __builtins__}

        try:
            exec(source.strip(), exec_globals, local_vars)  # nosec
            return local_vars.get("output", inputs)
        except Exception as exc:
            raise RuntimeError(f"Code execution error: {exc}") from exc

    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "title": "Python Code",
                    "description": "Python code. Use `inputs` dict, set `output` dict.",
                    "default": "# Write Python code here\noutput = inputs",
                },
            },
        }

    @classmethod
    def get_input_schema(cls) -> dict:
        return {"type": "object", "properties": {}}

    @classmethod
    def get_output_schema(cls) -> dict:
        return {"type": "object", "properties": {}}
