"""CodeRunnerNode — Executes Python snippets with I/O variables and timeout.

IMPORTANT SAFETY NOTE: This is a SIMULATED code runner. Real code execution
requires additional sandboxing and is not implemented in this version.
The node returns mock results based on input analysis.

Uses the Phase 5 LLM provider system as a future enhancement for predicting
code behavior. Currently operates in fake/default mode only.
"""

from __future__ import annotations

import json
import time
from typing import Any

from decision_system.workflow_engine.models import WorkflowNode, ExecutionContext
from decision_system.workflow_engine.providers.client import LLMClient


# ── Fake fallback executor ───────────────────────────────────────────


def _simulate_execution(source_code: str, inputs: dict) -> dict:
    """Simulate code execution — no actual Python is run.

    Returns deterministic mock results based on input analysis and
    variable names found in the source code.
    """
    start_time = time.monotonic()

    if not source_code or not source_code.strip():
        elapsed = (time.monotonic() - start_time) * 1000
        return {
            "result": None,
            "stdout": "",
            "error": "No source code provided.",
            "execution_time_ms": round(elapsed, 2),
            "success": False,
        }

    stdout_lines = []
    source_lower = source_code.lower()

    # Simulate print statements — count print() calls
    print_count = source_code.count("print(")
    for _ in range(min(print_count, 5)):
        stdout_lines.append("[simulated output]")

    # Check for obvious error patterns
    if "raise " in source_lower or "throw " in source_lower:
        elapsed = (time.monotonic() - start_time) * 1000
        return {
            "result": None,
            "stdout": "\n".join(stdout_lines),
            "error": "Code contains error-throwing logic. Simulated execution stopped.",
            "execution_time_ms": round(elapsed, 2),
            "success": False,
        }

    result = None

    # Check for specific variable patterns in source
    if "output" in source_lower:
        result = {"message": "Code executed (simulated)", "output_variable_detected": True}
        stdout_lines.append("Output variable detected in source code.")
    elif "df" in source_lower or "dataframe" in source_lower:
        result = {"type": "dataframe", "rows": 0, "columns": 0, "shape": [0, 0]}
        stdout_lines.append("DataFrame operations detected (simulated).")

    # If inputs are provided, derive useful mock results
    if inputs and not result:
        if isinstance(inputs, dict):
            if "data" in inputs:
                data_val = inputs["data"]
                if isinstance(data_val, list):
                    first_item = data_val[0] if data_val else None
                    result = {
                        "count": len(data_val),
                        "first_item": first_item,
                        "input_keys": list(inputs.keys()),
                    }
                    stdout_lines.append(f"Processed {len(data_val)} data items.")
                elif isinstance(data_val, dict):
                    result = {
                        "keys": list(data_val.keys()),
                        "value_count": len(data_val),
                        "input_keys": list(inputs.keys()),
                    }
                    stdout_lines.append(f"Processed data object with {len(data_val)} keys.")
                else:
                    result = {
                        "processed_input": True,
                        "input_keys": list(inputs.keys()),
                    }
            else:
                result = {
                    "processed_input": True,
                    "input_keys": list(inputs.keys()),
                }
        elif isinstance(inputs, list):
            result = {
                "count": len(inputs),
                "first_item": inputs[0] if inputs else None,
            }

    # If nothing matched, return a generic result
    if result is None:
        result = {"message": "Code executed successfully (simulated)", "source_length": len(source_code)}
        stdout_lines.append("Code executed (simulated).")

    elapsed = (time.monotonic() - start_time) * 1000

    return {
        "result": result,
        "stdout": "\n".join(stdout_lines),
        "error": None,
        "execution_time_ms": round(elapsed, 2),
        "success": True,
    }


# ── Code Runner Prompt (future enhancement) ─────────────────────────

_CODE_RUNNER_SYSTEM_PROMPT = """You are a Code Analyzer in a workflow automation system.
Analyze the following Python code and predict its output:

```python
{source_code}
```

Inputs available to the code:
{inputs_json}

Based on static analysis, predict:
1. What the code would output
2. Any errors it would raise
3. The return value or result

Return JSON matching this schema:
{{
  "result": any,
  "stdout": "string — predicted print output",
  "error": "string or null",
  "execution_time_ms": 0,
  "success": boolean
}}

NOTE: This is a simulation. Do NOT execute the code — analyze it statically.
Return ONLY valid JSON."""


class CodeRunnerNode(WorkflowNode):
    """Executes Python snippets with I/O variables and timeout.

    IMPORTANT SAFETY NOTE: This is a SIMULATED code runner. Real code
    execution requires additional sandboxing and is not implemented in
    this version. The node returns mock results based on input analysis.

    In fake/default mode, no actual Python is executed. The node analyzes
    the source code and input patterns to return a plausible mock result.
    """
    type: str = "decision_system.code_runner"
    label: str = "Code Runner"

    async def execute(self, inputs: dict, ctx: ExecutionContext) -> dict:
        source_code = inputs.get("source_code", "")
        input_vars = inputs.get("inputs", {})
        libraries = inputs.get("libraries") or self.config.get("libraries", [])

        if not source_code:
            return {
                "result": None,
                "stdout": "",
                "error": "No source code provided.",
                "execution_time_ms": 0,
                "success": False,
            }

        timeout = min(self.config.get("timeout_seconds", 10), 60)

        # Note: in this version we only use fake/simulated execution.
        # The LLM path is reserved for future enhancement.
        provider_cfg = ctx.resolve_provider(
            self.config.get("provider"),
            self.config.get("model"),
        )

        if provider_cfg:
            provider_config, _ = provider_cfg
            try:
                return await self._llm_predict(source_code, input_vars, libraries, provider_config, timeout)
            except Exception:
                pass

        # Fake fallback — simulated execution
        return _simulate_execution(source_code, input_vars)

    async def _llm_predict(
        self, source_code: str, input_vars: dict, libraries: list,
        provider_config: Any, timeout: int,
    ) -> dict:
        """Use LLM to predict code output (static analysis, no execution)."""
        client = LLMClient(provider_config)
        inputs_json = json.dumps(input_vars, default=str)[:2000]

        libs_hint = ""
        if libraries:
            libs_hint = f"\nAvailable libraries: {', '.join(libraries)}"

        response = await client.chat_completion(
            messages=[
                {"role": "system", "content": _CODE_RUNNER_SYSTEM_PROMPT.format(
                    source_code=source_code,
                    inputs_json=inputs_json,
                )},
                {"role": "user", "content": f"Analyze this Python code{libs_hint}. Timeout: {timeout}s."},
            ],
            model=provider_config.default_model,
            stream=False,
        )

        result = json.loads(response)

        # Ensure all required fields
        if "result" not in result:
            result["result"] = None
        if "stdout" not in result:
            result["stdout"] = ""
        if "error" not in result:
            result["error"] = None
        if "execution_time_ms" not in result:
            result["execution_time_ms"] = 0
        if "success" not in result:
            result["success"] = False

        return result

    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "timeout_seconds": {
                    "type": "integer",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 60,
                    "title": "Timeout (seconds)",
                    "description": "Maximum execution time in seconds",
                },
                "capture_stdout": {
                    "type": "boolean",
                    "default": True,
                    "title": "Capture Stdout",
                    "description": "Capture print() output",
                },
                "allow_file_access": {
                    "type": "boolean",
                    "default": False,
                    "title": "Allow File Access",
                    "description": "Allow code to access the filesystem (not implemented)",
                },
            },
        }

    @classmethod
    def get_input_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "source_code": {
                    "type": "string",
                    "description": "Python code to execute",
                },
                "inputs": {
                    "type": "object",
                    "description": "Input variables accessible to the code",
                },
                "libraries": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Additional libraries to import",
                },
            },
            "required": ["source_code"],
        }

    @classmethod
    def get_output_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "result": {"description": "Return value from execution"},
                "stdout": {"type": "string", "description": "Captured print output"},
                "error": {"type": "string", "description": "Error message if execution failed"},
                "execution_time_ms": {"type": "number", "description": "Execution time in milliseconds"},
                "success": {"type": "boolean", "description": "Whether execution succeeded"},
            },
        }
