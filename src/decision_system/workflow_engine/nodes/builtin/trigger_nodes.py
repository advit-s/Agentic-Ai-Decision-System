"""Built-in trigger and input node types."""

from __future__ import annotations

from decision_system.workflow_engine.models import (
    WorkflowNode, ExecutionContext,
)


class ManualTriggerNode(WorkflowNode):
    """Manual trigger — starts a workflow with provided inputs.
    This is the default trigger for on-demand workflow execution.
    """
    type: str = "decision_system.trigger_manual"
    label: str = "Manual Trigger"

    async def execute(self, inputs: dict, ctx: ExecutionContext) -> dict:
        return {"triggered": True, **inputs}

    @classmethod
    def get_config_schema(cls) -> dict:
        return {"type": "object", "properties": {}}

    @classmethod
    def get_input_schema(cls) -> dict:
        return {"type": "object", "properties": {}}

    @classmethod
    def get_output_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "triggered": {"type": "boolean"},
            },
        }


class InputTextNode(WorkflowNode):
    """Provides a text input to the workflow.
    Useful for injecting question text, prompts, or configuration.
    """
    type: str = "decision_system.input_text"
    label: str = "Input Text"

    async def execute(self, inputs: dict, ctx: ExecutionContext) -> dict:
        text = self.config.get("text", "")
        return {"text": text, "question": text}

    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "title": "Text",
                    "description": "The text to provide as input",
                },
            },
            "required": ["text"],
        }

    @classmethod
    def get_input_schema(cls) -> dict:
        return {"type": "object", "properties": {}}

    @classmethod
    def get_output_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "question": {"type": "string"},
            },
        }
