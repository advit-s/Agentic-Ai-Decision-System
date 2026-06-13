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


class CronTriggerNode(WorkflowNode):
    """Cron trigger — starts a workflow on a time-based schedule.

    The scheduler evaluates the cron expression and fires the workflow
    automatically when the expression matches the current time.
    During manual execution this node simply passes through the
    configured schedule info.
    """
    type: str = "decision_system.trigger_cron"
    label: str = "Cron Trigger"

    async def execute(self, inputs: dict, ctx: ExecutionContext) -> dict:
        expression = self.config.get("expression", "0 9 * * *")
        return {
            "trigger_type": "cron",
            "expression": expression,
            "triggered": True,
        }

    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "title": "Cron Expression",
                    "description": (
                        "Schedule in cron format: "
                        "minute hour day-of-month month day-of-week"
                    ),
                    "default": "0 9 * * *",
                    "examples": [
                        "0 9 * * 1-5",    # Weekdays at 9am
                        "*/30 * * * *",   # Every 30 minutes
                        "0 0 * * *",      # Daily at midnight
                        "0 8 * * 1",      # Mondays at 8am
                    ],
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
                "trigger_type": {"type": "string"},
                "expression": {"type": "string"},
                "triggered": {"type": "boolean"},
            },
        }


class WebhookTriggerNode(WorkflowNode):
    """Webhook trigger — starts a workflow via HTTP POST.

    The scheduler registers a unique webhook URL for this node.
    POSTing to the webhook URL triggers the workflow with the
    POST body passed as workflow inputs.
    """
    type: str = "decision_system.trigger_webhook"
    label: str = "Webhook Trigger"

    async def execute(self, inputs: dict, ctx: ExecutionContext) -> dict:
        path = self.config.get("webhook_path", "")
        return {
            "trigger_type": "webhook",
            "webhook_path": path,
            "triggered": True,
            **inputs,
        }

    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "webhook_path": {
                    "type": "string",
                    "title": "Webhook Path",
                    "description": "Auto-generated unique path for this webhook",
                    "default": "",
                },
            },
        }

    @classmethod
    def get_input_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "payload": {
                    "type": "object",
                    "title": "Webhook Payload",
                    "description": "JSON body from the webhook POST request",
                },
            },
        }

    @classmethod
    def get_output_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "trigger_type": {"type": "string"},
                "webhook_path": {"type": "string"},
                "triggered": {"type": "boolean"},
            },
        }


class FileWatchTriggerNode(WorkflowNode):
    """File Watch trigger — starts a workflow when files change in a directory.

    The scheduler monitors the configured directory for new or modified
    files matching the pattern. When detected, it fires the workflow.
    """
    type: str = "decision_system.trigger_file_watch"
    label: str = "File Watch Trigger"

    async def execute(self, inputs: dict, ctx: ExecutionContext) -> dict:
        directory = self.config.get("directory", "")
        pattern = self.config.get("pattern", "*")
        changed_files = inputs.get("_changed_files", [])
        return {
            "trigger_type": "file_watch",
            "directory": directory,
            "pattern": pattern,
            "changed_files": changed_files,
            "triggered": True,
        }

    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "directory": {
                    "type": "string",
                    "title": "Directory to Watch",
                    "description": "Path to the directory to monitor",
                    "default": "company_docs/",
                },
                "pattern": {
                    "type": "string",
                    "title": "File Pattern",
                    "description": "Glob pattern for files to watch (e.g. *.md, *.csv)",
                    "default": "*",
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
                "trigger_type": {"type": "string"},
                "directory": {"type": "string"},
                "pattern": {"type": "string"},
                "changed_files": {"type": "array"},
                "triggered": {"type": "boolean"},
            },
        }
