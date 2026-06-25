"""AuditorNode — Reviews data for quality, completeness, and consistency.

Uses the Phase 5 LLM provider system for AI-powered auditing,
with deterministic fake fallback when no provider is configured.
"""

from __future__ import annotations

import json
from typing import Any

from decision_system.workflow_engine.models import ExecutionContext, WorkflowNode
from decision_system.workflow_engine.providers.client import LLMClient

# ── Fake fallback generators ─────────────────────────────────────────


def _generate_fake_audit(data: dict, audit_depth: str) -> dict:
    """Generate deterministic mock audit results based on data keys."""
    data_keys = " ".join(data.keys()).lower()
    findings: list[dict[str, Any]] = []
    score = 0.7
    passed = False

    if "finding" in data_keys or "findings" in data_keys:
        raw_findings = data.get("findings") or data.get("finding") or []
        if isinstance(raw_findings, list):
            for i, f in enumerate(raw_findings[:5]):
                confidence = f.get("confidence", 0.5) if isinstance(f, dict) else 0.5
                evidence = f.get("evidence", []) if isinstance(f, dict) else []
                findings.append(
                    {
                        "category": "evidence_quality",
                        "severity": "medium" if confidence < 0.5 else "low",
                        "description": f"Finding {i + 1} has confidence {confidence:.1f} with {len(evidence) if isinstance(evidence, list) else 0} evidence items.",
                        "recommendation": "Strengthen evidence base for this finding.",
                    }
                )
        score = 0.75 if len(findings) == 0 else max(0.3, 0.75 - len(findings) * 0.08)
    elif "analysis" in data_keys:
        findings.append(
            {
                "category": "completeness",
                "severity": "low",
                "description": "Analysis data appears structurally complete.",
                "recommendation": "Consider adding more granular breakdowns.",
            }
        )
        findings.append(
            {
                "category": "consistency",
                "severity": "medium",
                "description": "Analysis methods appear consistent across data points.",
                "recommendation": "Verify edge cases and outlier handling.",
            }
        )
        score = 0.78
    elif "plan" in data_keys:
        plan_steps = data.get("plan") or data.get("steps") or []
        if isinstance(plan_steps, list):
            for i, step in enumerate(plan_steps[:5]):
                if isinstance(step, dict) and not step.get("dependencies"):
                    findings.append(
                        {
                            "category": "completeness",
                            "severity": "low",
                            "description": f"Step {i + 1} is missing dependency information.",
                            "recommendation": "Add dependency references for better sequencing.",
                        }
                    )
                if isinstance(step, dict) and not step.get("estimated_effort"):
                    findings.append(
                        {
                            "category": "completeness",
                            "severity": "medium",
                            "description": f"Step {i + 1} has no effort estimate.",
                            "recommendation": "Add time or effort estimates for each step.",
                        }
                    )
        score = max(0.3, 0.8 - len(findings) * 0.1)
    else:
        # Basic quality check
        total_fields = len(data)
        findings.append(
            {
                "category": "completeness",
                "severity": "low",
                "description": f"Data contains {total_fields} top-level fields. Basic structure check passed.",
                "recommendation": "Review data for completeness against expected schema.",
            }
        )
        score = 0.7

    if audit_depth == "quick":
        findings = findings[:2]
        score = min(score + 0.1, 1.0)
    elif audit_depth == "thorough":
        extra = {
            "category": "consistency",
            "severity": "low",
            "description": "Cross-referenced data fields for internal consistency.",
            "recommendation": "No consistency issues detected.",
        }
        findings.append(extra)
        score = max(0.0, score - 0.05)

    passed = score >= 0.6
    issues_found = len(findings)
    recommendations = [f["recommendation"] for f in findings]

    return {
        "passed": passed,
        "score": round(score, 2),
        "findings": findings,
        "summary": f"Audit complete. {issues_found} issue(s) found. Score: {score:.0%}.",
        "issues_found": issues_found,
        "recommendations": recommendations,
    }


# ── Auditor Prompt ──────────────────────────────────────────────────

_AUDITOR_SYSTEM_PROMPT = """You are a Data Auditor in a workflow automation system.
Review the following data for quality, completeness, and consistency:

Data: {data_json}

Audit Scope: {audit_scope_str}
Audit Depth: {audit_depth}
Custom Criteria: {criteria_str}

Produce structured audit results as JSON matching this schema:
{{
  "passed": boolean,
  "score": 0.0-1.0,
  "findings": [
    {{
      "category": "string — e.g. completeness, consistency, accuracy",
      "severity": "low|medium|high",
      "description": "string",
      "recommendation": "string"
    }}
  ],
  "summary": "string",
  "issues_found": integer,
  "recommendations": ["string"]
}}

Assign each finding a severity level and actionable recommendation.
Return ONLY valid JSON."""


class AuditorNode(WorkflowNode):
    """Reviews data for quality, completeness, and consistency.

    Produces structured audit findings with severity levels and recommendations.
    Falls back to deterministic mock audit when no LLM provider is configured.
    """

    type: str = "decision_system.auditor"
    label: str = "Auditor"

    async def execute(self, inputs: dict, ctx: ExecutionContext) -> dict:
        data = inputs.get("data", {})
        audit_scope = inputs.get("audit_scope") or self.config.get(
            "audit_scope", ["completeness", "consistency"]
        )
        criteria = inputs.get("criteria", {})

        if not data:
            return {
                "passed": True,
                "score": 1.0,
                "findings": [],
                "summary": "No data to audit — nothing to review.",
                "issues_found": 0,
                "recommendations": [],
            }

        audit_depth = self.config.get("audit_depth", "standard")

        # Normalize data
        if isinstance(data, list):
            data = {"_items": data}

        audit_scope_str = ", ".join(audit_scope) if audit_scope else "all aspects"
        criteria_str = json.dumps(criteria) if criteria else "None"

        # Try real provider first
        provider_cfg = ctx.resolve_provider(
            self.config.get("provider"),
            self.config.get("model"),
        )

        fallback_reason = ""

        if provider_cfg:
            provider_config, _ = provider_cfg
            try:
                return await self._llm_audit(
                    data, audit_scope_str, audit_depth, criteria_str, provider_config
                )
            except Exception as exc:
                fallback_reason = f"{type(exc).__name__}: {exc}"

        # Fake fallback
        result = _generate_fake_audit(data, audit_depth)
        if fallback_reason:
            result["fallback_reason"] = fallback_reason
        else:
            result["fallback_reason"] = ""
        return result

    async def _llm_audit(
        self,
        data: dict,
        audit_scope_str: str,
        audit_depth: str,
        criteria_str: str,
        provider_config: Any,
    ) -> dict:
        """Use LLM to audit the data."""
        client = LLMClient(provider_config)
        data_json = json.dumps(data, default=str)[:3000]

        response = await client.chat_completion(
            messages=[
                {
                    "role": "system",
                    "content": _AUDITOR_SYSTEM_PROMPT.format(
                        data_json=data_json,
                        audit_scope_str=audit_scope_str,
                        audit_depth=audit_depth,
                        criteria_str=criteria_str,
                    ),
                },
                {
                    "role": "user",
                    "content": f"Audit this data ({audit_depth} depth, scope: {audit_scope_str}).",
                },
            ],
            model=provider_config.default_model,
            stream=False,
        )

        result = json.loads(response)

        # Ensure all required fields
        if "passed" not in result:
            result["passed"] = False
        if "score" not in result:
            result["score"] = 0.0
        if "findings" not in result:
            result["findings"] = []
        if "summary" not in result:
            result["summary"] = ""
        if "issues_found" not in result:
            result["issues_found"] = len(result.get("findings", []))
        if "recommendations" not in result:
            result["recommendations"] = []
        result["fallback_reason"] = ""

        return result

    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "audit_depth": {
                    "type": "string",
                    "default": "standard",
                    "enum": ["quick", "standard", "thorough"],
                    "title": "Audit Depth",
                    "description": "How thorough the audit should be",
                },
                "severity_threshold": {
                    "type": "string",
                    "default": "medium",
                    "enum": ["low", "medium", "high"],
                    "title": "Severity Threshold",
                    "description": "Minimum severity to report",
                },
                "fail_on_issues": {
                    "type": "boolean",
                    "default": False,
                    "title": "Fail on Issues",
                    "description": "Whether the node fails if issues are found",
                },
            },
        }

    @classmethod
    def get_input_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "data": {
                    "type": "object",
                    "description": "The data to audit",
                },
                "audit_scope": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "What aspects to check (e.g. completeness, consistency)",
                },
                "criteria": {
                    "type": "object",
                    "description": "Custom audit criteria",
                },
            },
            "required": ["data"],
        }

    @classmethod
    def get_output_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "passed": {"type": "boolean", "description": "Overall pass/fail"},
                "score": {
                    "type": "number",
                    "description": "Overall quality score (0-1)",
                },
                "findings": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "category": {"type": "string"},
                            "severity": {
                                "type": "string",
                                "enum": ["low", "medium", "high"],
                            },
                            "description": {"type": "string"},
                            "recommendation": {"type": "string"},
                        },
                    },
                },
                "summary": {"type": "string"},
                "issues_found": {"type": "integer"},
                "recommendations": {"type": "array", "items": {"type": "string"}},
                "fallback_reason": {"type": "string"},
            },
        }
