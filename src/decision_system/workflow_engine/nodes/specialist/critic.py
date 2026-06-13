"""CriticNode — Reviews outputs from other nodes for quality issues.

Checks for contradictions, unsupported claims, logical fallacies,
and confidence calibration. Uses LLM when available, deterministic
rule-based checks as fake fallback.
"""

from __future__ import annotations

import json
from typing import Any

from decision_system.workflow_engine.models import WorkflowNode, ExecutionContext
from decision_system.workflow_engine.providers.client import LLMClient


# ── Fallacy trigger phrases ───────────────────────────────────────────

_FALLACY_PHRASES: list[tuple[str, str]] = [
    ("everyone knows", "appeal_to_common_belief"),
    ("clearly", "false_authority"),
    ("obviously", "appeal_to_obviousness"),
    ("it is well known that", "appeal_to_tradition"),
    ("anyone would agree", "appeal_to_common_belief"),
    ("studies prove", "vague_authority"),
    ("everyone says", "bandwagon"),
    ("it goes without saying", "begging_the_question"),
]

_NEGATION_PAIRS: list[tuple[str, str]] = [
    ("increased", "decreased"),
    ("grew", "shrank"),
    ("rose", "fell"),
    ("up", "down"),
    ("higher", "lower"),
    ("positive", "negative"),
    ("profit", "loss"),
    ("gain", "decline"),
    ("improved", "worsened"),
    ("strengthened", "weakened"),
]


# ── Deterministic rule checks ─────────────────────────────────────────

def _normalize_claims_list(target_data: dict) -> list[dict[str, Any]]:
    """Normalize various input formats to a list of claim dicts."""
    if isinstance(target_data, list):
        return target_data
    if isinstance(target_data, dict):
        # Check for claims_list format
        if "statements" in target_data or "claims" in target_data:
            raw = target_data.get("claims") or target_data.get("statements") or []
            if isinstance(raw, list):
                return raw
        # Check for findings_list format
        if "findings" in target_data:
            return target_data["findings"]
        # Single claim
        if "statement" in target_data or "text" in target_data:
            return [target_data]
    return []


def _check_contradictions(claims: list[dict]) -> list[dict]:
    """Check for contradictory pairs at the string level."""
    issues = []
    for i in range(len(claims)):
        for j in range(i + 1, len(claims)):
            text_i = claims[i].get("statement", claims[i].get("text", "")).lower()
            text_j = claims[j].get("statement", claims[j].get("text", "")).lower()
            for pos, neg in _NEGATION_PAIRS:
                if pos in text_i and neg in text_j:
                    issues.append({
                        "type": "contradiction",
                        "severity": "medium",
                        "location": f"Claim {i + 1} vs Claim {j + 1}",
                        "description": f"'{claims[i].get('statement', text_i)}' conflicts with '{claims[j].get('statement', text_j)}'",
                        "suggestion": "Review both claims and reconcile the direction of change.",
                    })
                    break
    return issues


def _check_unsupported(claims: list[dict]) -> list[dict]:
    """Check claims with missing or empty evidence."""
    issues = []
    for i, claim in enumerate(claims):
        evidence = claim.get("evidence") or claim.get("chunks") or claim.get("sources") or []
        if not evidence or all(not e for e in evidence if isinstance(e, str)):
            issues.append({
                "type": "unsupported",
                "severity": "high",
                "location": f"Claim {i + 1}",
                "description": f"Claim '{claim.get('statement', claim.get('text', ''))[:80]}' has no supporting evidence.",
                "suggestion": "Add evidence citations or mark as unsupported.",
            })
    return issues


def _check_fallacies(text: str) -> list[dict]:
    """Pattern-match for common logical fallacy trigger phrases."""
    issues = []
    text_lower = text.lower()
    for phrase, fallacy_type in _FALLACY_PHRASES:
        if phrase in text_lower:
            issues.append({
                "type": "logical_fallacy",
                "severity": "low",
                "location": f"Text containing '{phrase}'",
                "description": f"Potential '{fallacy_type}' fallacy detected via phrase '{phrase}'.",
                "suggestion": "Replace with specific evidence or reasoning.",
            })
    return issues


def _check_confidence(claims: list[dict]) -> list[dict]:
    """Flag high-confidence claims with thin or missing evidence."""
    issues = []
    for i, claim in enumerate(claims):
        confidence = claim.get("confidence", 0.5)
        if isinstance(confidence, (int, float)) and confidence > 0.8:
            evidence = claim.get("evidence") or claim.get("chunks") or claim.get("sources") or []
            if not evidence or len(evidence) < 2:
                issues.append({
                    "type": "misconfidence",
                    "severity": "medium",
                    "location": f"Claim {i + 1}",
                    "description": f"Confidence {confidence:.1f} with {len(evidence)} evidence source(s).",
                    "suggestion": "Reduce confidence or add supporting evidence.",
                })
    return issues


def _combine_text(claims: list[dict]) -> str:
    """Combine claim statements into continuous text for fallacy checking."""
    texts = []
    for c in claims:
        t = c.get("statement", c.get("text", c.get("description", "")))
        if isinstance(t, str):
            texts.append(t)
    return " ".join(texts)


# ── Critic Prompt ────────────────────────────────────────────────────

_CRITIC_SYSTEM_PROMPT = """You are a Critic/Judge in a workflow automation system.
Review the following set of claims or text for quality issues.

Analyze based on these criteria (enabled: {enabled_criteria}):

1. **contradictions**: Pairwise comparison for logical conflicts
2. **unsupported_claims**: Identify claims without adequate evidence
3. **logical_fallacies**: Pattern-match for common reasoning errors
4. **confidence_calibration**: Flag high-confidence claims with thin evidence

Return JSON matching this schema:
{{
  "passed": true/false,
  "issues": [
    {{
      "type": "contradiction|unsupported|logical_fallacy|misconfidence",
      "severity": "low|medium|high",
      "location": "where the issue occurs",
      "description": "what the issue is",
      "suggestion": "how to fix it"
    }}
  ],
  "summary": "concise evaluation summary",
  "confidence_adjustment": -0.0
}}

Set 'passed' to false if any issue has severity >= medium.
confidence_adjustment should be negative (e.g. -0.2) when issues found, 0.0 if clean.
Return ONLY valid JSON."""


class CriticNode(WorkflowNode):
    """Reviews outputs from other nodes for quality issues.

    Checks for contradictions, unsupported claims, logical fallacies,
    and confidence calibration. Uses LLM when available, deterministic
    rule-based checks as fake fallback.
    """
    type: str = "decision_system.critic"
    label: str = "Critic / Judge"

    async def execute(self, inputs: dict, ctx: ExecutionContext) -> dict:
        target_type = inputs.get("target_type", "claims_list")
        target_data = inputs.get("target_data", {})
        context = inputs.get("context", "")

        if not target_data:
            return {
                "passed": True,
                "issues": [],
                "summary": "Nothing to review — empty input.",
                "confidence_adjustment": 0.0,
                "fallback_reason": "",
            }

        enabled_criteria = self.config.get("criteria", ["contradictions", "unsupported_claims"])
        strictness = self.config.get("strictness", "balanced")
        max_issues = self.config.get("max_issues", 20)

        # Normalize input
        claims = _normalize_claims_list(target_data)

        if claims:
            # Deterministic checks first — we always run these
            issues: list[dict] = []
            if "contradictions" in enabled_criteria:
                issues.extend(_check_contradictions(claims))
            if "unsupported_claims" in enabled_criteria:
                issues.extend(_check_unsupported(claims))
            if "logical_fallacies" in enabled_criteria:
                combined = _combine_text(claims)
                issues.extend(_check_fallacies(combined))
            if "confidence_calibration" in enabled_criteria:
                issues.extend(_check_confidence(claims))

            # Apply strictness filter
            severity_map = {"lenient": ["high"], "balanced": ["medium", "high"], "strict": ["low", "medium", "high"]}
            allowed_severities = severity_map.get(strictness, ["medium", "high"])
            issues = [i for i in issues if i["severity"] in allowed_severities]

            # Try LLM for deeper analysis
            provider_cfg = ctx.resolve_provider(
                self.config.get("provider"),
                self.config.get("model"),
            )

            if provider_cfg:
                provider_config, _ = provider_cfg
                try:
                    llm_issues = await self._llm_review(claims, context, enabled_criteria, provider_config)
                    # Merge: use LLM issues when available, supplement with deterministic
                    if llm_issues:
                        issues = llm_issues
                except Exception:
                    pass  # Keep deterministic issues on LLM failure

            # Apply max_issues
            if len(issues) > max_issues:
                issues = issues[:max_issues]

            passed = not any(i["severity"] in ("medium", "high") for i in issues)
            conf_adj = -min(len(issues) * 0.1, 0.5) if issues else 0.0

            return {
                "passed": passed,
                "issues": issues,
                "summary": f"Found {len(issues)} issue(s). {'All clean.' if passed else 'Review recommended.'}",
                "confidence_adjustment": conf_adj,
                "fallback_reason": "",
            }

        # Report text or findings (non-claims path) — try LLM
        provider_cfg = ctx.resolve_provider(
            self.config.get("provider"),
            self.config.get("model"),
        )
        if provider_cfg:
            provider_config, _ = provider_cfg
            try:
                return await self._llm_review_report(target_data, context, enabled_criteria, provider_config)
            except Exception:
                pass

        # Fallback for non-claims input — do basic text-level check
        text = str(target_data)
        issues = _check_fallacies(text) if "logical_fallacies" in enabled_criteria else []
        passed = not any(i["severity"] in ("medium", "high") for i in issues)
        return {
            "passed": passed,
            "issues": issues,
            "summary": f"Reviewed text: found {len(issues)} potential issue(s).",
            "confidence_adjustment": -0.1 if issues else 0.0,
            "fallback_reason": "",
        }

    async def _llm_review(
        self, claims: list[dict], context: str, enabled_criteria: list[str], provider_config: Any,
    ) -> list[dict]:
        """Use LLM to review claims."""
        client = LLMClient(provider_config)
        claims_text = json.dumps(claims, indent=2)

        response = await client.chat_completion(
            messages=[
                {"role": "system", "content": _CRITIC_SYSTEM_PROMPT.format(
                    enabled_criteria=", ".join(enabled_criteria),
                )},
                {"role": "user", "content": f"Review these claims:\n{claims_text}\n\nContext: {context}"},
            ],
            model=provider_config.default_model,
            stream=False,
        )

        result = json.loads(response)
        return result.get("issues", [])

    async def _llm_review_report(
        self, target_data: Any, context: str, enabled_criteria: list[str], provider_config: Any,
    ) -> dict:
        """Use LLM to review a report or free-text output."""
        client = LLMClient(provider_config)
        text = json.dumps(target_data, indent=2) if isinstance(target_data, dict) else str(target_data)

        response = await client.chat_completion(
            messages=[
                {"role": "system", "content": _CRITIC_SYSTEM_PROMPT.format(
                    enabled_criteria=", ".join(enabled_criteria),
                )},
                {"role": "user", "content": f"Review this report/text:\n{text}\n\nContext: {context}"},
            ],
            model=provider_config.default_model,
            stream=False,
        )

        result = json.loads(response)
        if "issues" not in result:
            result["issues"] = []
        if "passed" not in result:
            result["passed"] = not any(i.get("severity") in ("medium", "high") for i in result["issues"])
        if "confidence_adjustment" not in result:
            result["confidence_adjustment"] = -0.2 if result["issues"] else 0.0
        if "summary" not in result:
            result["summary"] = f"Found {len(result['issues'])} issue(s)."
        result["fallback_reason"] = ""
        return result

    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "criteria": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["contradictions", "unsupported_claims", "logical_fallacies", "confidence_calibration"],
                    },
                    "default": ["contradictions", "unsupported_claims"],
                    "title": "Review Criteria",
                    "description": "Which quality checks to run",
                    "uniqueItems": True,
                },
                "strictness": {
                    "type": "string",
                    "default": "balanced",
                    "enum": ["lenient", "balanced", "strict"],
                    "title": "Strictness",
                },
                "max_issues": {
                    "type": "integer", "default": 20, "minimum": 1, "maximum": 100,
                    "title": "Max Issues",
                },
            },
        }

    @classmethod
    def get_input_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "target_type": {
                    "type": "string",
                    "enum": ["claims_list", "report_text", "findings_list"],
                    "default": "claims_list",
                    "description": "Format of the data to review",
                },
                "target_data": {
                    "type": "object",
                    "description": "Claims, report, or findings to review",
                },
                "context": {
                    "type": "string",
                    "default": "",
                    "description": "Additional context for the review",
                },
            },
            "required": ["target_data"],
        }

    @classmethod
    def get_output_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "passed": {"type": "boolean"},
                "issues": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string", "enum": ["contradiction", "unsupported", "logical_fallacy", "misconfidence"]},
                            "severity": {"type": "string", "enum": ["low", "medium", "high"]},
                            "location": {"type": "string"},
                            "description": {"type": "string"},
                            "suggestion": {"type": "string"},
                        },
                    },
                },
                "summary": {"type": "string"},
                "confidence_adjustment": {"type": "number"},
                "fallback_reason": {"type": "string"},
            },
        }
