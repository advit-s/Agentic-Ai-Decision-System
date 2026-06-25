"""ComplianceCheckerNode — Checks data against compliance rules and policies.

Uses the Phase 5 LLM provider system for AI-powered compliance checking,
with deterministic fake fallback when no provider is configured.
"""

from __future__ import annotations

import json
from typing import Any

from decision_system.workflow_engine.models import ExecutionContext, WorkflowNode
from decision_system.workflow_engine.providers.client import LLMClient

# ── Fake fallback generators ─────────────────────────────────────────


def _generate_fake_compliance(data: dict, framework: str, strict_mode: bool) -> dict:
    """Generate deterministic mock compliance results based on framework and data."""
    data_keys = " ".join(data.keys()).lower()
    violations: list[dict[str, Any]] = []
    passed_checks = 0
    failed_checks = 0
    risk_level = "low"
    score = 0.95

    if framework == "gdpr":
        # Check for data privacy indicators
        has_privacy_terms = any(kw in data_keys for kw in ("privacy", "consent", "pii", "personal"))
        has_data_subject = any(kw in data_keys for kw in ("subject", "user_data", "customer_data"))
        has_retention = any(kw in data_keys for kw in ("retention", "deletion", "expiry"))

        if not has_privacy_terms:
            violations.append(
                {
                    "rule": "GDPR-ART-5",
                    "severity": "critical",
                    "description": "No data privacy terms or consent indicators found in data.",
                    "remediation": "Implement consent management and privacy notice documentation.",
                }
            )
            failed_checks += 1
        else:
            passed_checks += 1

        if not has_data_subject:
            violations.append(
                {
                    "rule": "GDPR-ART-15",
                    "severity": "high",
                    "description": "Data subject access request handling not evident.",
                    "remediation": "Establish data subject access request (DSAR) process.",
                }
            )
            failed_checks += 1
        else:
            passed_checks += 1

        if not has_retention:
            violations.append(
                {
                    "rule": "GDPR-ART-17",
                    "severity": "medium",
                    "description": "Data retention and deletion policies not clearly defined.",
                    "remediation": "Define data retention periods and implement automated deletion.",
                }
            )
            failed_checks += 1
        else:
            passed_checks += 1

    elif framework == "soc2":
        # Check for security controls
        has_access_control = any(kw in data_keys for kw in ("access", "auth", "permission"))
        has_monitoring = any(kw in data_keys for kw in ("monitor", "audit_log", "logging"))
        has_encryption = any(kw in data_keys for kw in ("encrypt", "crypto", "tls", "https"))

        if not has_access_control:
            violations.append(
                {
                    "rule": "SOC2-CC6",
                    "severity": "high",
                    "description": "No access control mechanisms identified in data.",
                    "remediation": "Implement role-based access control (RBAC) and review access logs.",
                }
            )
            failed_checks += 1
        else:
            passed_checks += 1

        if not has_monitoring:
            violations.append(
                {
                    "rule": "SOC2-CC7",
                    "severity": "high",
                    "description": "No monitoring or audit logging detected.",
                    "remediation": "Deploy monitoring and audit logging for system activity.",
                }
            )
            failed_checks += 1
        else:
            passed_checks += 1

        if not has_encryption:
            violations.append(
                {
                    "rule": "SOC2-CC6.7",
                    "severity": "medium",
                    "description": "Encryption indicators not found — data may not be encrypted at rest or in transit.",
                    "remediation": "Implement encryption for data at rest and in transit.",
                }
            )
            failed_checks += 1
        else:
            passed_checks += 1

    elif framework == "hipaa":
        # Check for health data safeguards
        has_phi_safeguards = any(kw in data_keys for kw in ("phi", "health", "medical", "patient"))
        has_breach_notification = any(
            kw in data_keys for kw in ("breach", "notification", "incident")
        )
        has_access_logs = any(kw in data_keys for kw in ("access_log", "audit", "login"))

        if not has_phi_safeguards:
            violations.append(
                {
                    "rule": "HIPAA-164.312",
                    "severity": "critical",
                    "description": "No PHI safeguards detected. Protected health information may not be properly secured.",
                    "remediation": "Implement administrative, physical, and technical safeguards for PHI.",
                }
            )
            failed_checks += 1
        else:
            passed_checks += 1

        if not has_breach_notification:
            violations.append(
                {
                    "rule": "HIPAA-164.410",
                    "severity": "high",
                    "description": "Breach notification process not evident in data.",
                    "remediation": "Establish breach notification procedures as required by HIPAA.",
                }
            )
            failed_checks += 1
        else:
            passed_checks += 1

        if not has_access_logs:
            violations.append(
                {
                    "rule": "HIPAA-164.312(b)",
                    "severity": "medium",
                    "description": "Access log mechanisms not detected.",
                    "remediation": "Implement audit controls to record access to PHI.",
                }
            )
            failed_checks += 1
        else:
            passed_checks += 1

    elif framework == "internal":
        # Check for basic completeness
        has_metadata = any(kw in data_keys for kw in ("metadata", "version", "date", "timestamp"))
        has_owner = any(kw in data_keys for kw in ("owner", "author", "creator"))
        has_status = any(kw in data_keys for kw in ("status", "state", "phase"))

        if not has_metadata:
            violations.append(
                {
                    "rule": "INT-META-001",
                    "severity": "medium",
                    "description": "Data missing metadata fields (version, date, or timestamp).",
                    "remediation": "Add metadata including version, creation date, and last modified date.",
                }
            )
            failed_checks += 1
        else:
            passed_checks += 1

        if not has_owner:
            violations.append(
                {
                    "rule": "INT-OWN-001",
                    "severity": "medium",
                    "description": "Data owner or author not identified.",
                    "remediation": "Assign a data owner for accountability.",
                }
            )
            failed_checks += 1
        else:
            passed_checks += 1

        if not has_status:
            violations.append(
                {
                    "rule": "INT-STAT-001",
                    "severity": "low",
                    "description": "Data status or state field is missing.",
                    "remediation": "Add status field to track data lifecycle state.",
                }
            )
            failed_checks += 1
        else:
            passed_checks += 1

    else:
        # Custom / unknown framework — warning
        violations.append(
            {
                "rule": "FRM-GEN-001",
                "severity": "low",
                "description": f"No specific compliance rules defined for framework: '{framework}'.",
                "remediation": f"Define compliance rules for {framework} or select a supported framework (gdpr, soc2, hipaa, internal).",
            }
        )
        failed_checks += 1

    if strict_mode:
        # Flag anything borderline as violations
        if len(violations) == 0:
            violations.append(
                {
                    "rule": "STRICT-001",
                    "severity": "low",
                    "description": "Strict mode enabled — no issues found but review recommended.",
                    "remediation": "Manual review recommended to ensure full compliance.",
                }
            )
            passed_checks = max(0, passed_checks - 1)
            failed_checks += 1

    total_checks = passed_checks + failed_checks
    if total_checks > 0:
        score = passed_checks / total_checks
    else:
        score = 1.0

    # Risk level
    severities = [v["severity"] for v in violations]
    if "critical" in severities:
        risk_level = "critical"
    elif "high" in severities:
        risk_level = "high"
    elif "medium" in severities:
        risk_level = "medium"
    else:
        risk_level = "low"

    compliant = failed_checks == 0

    summary_parts = []
    if compliant:
        summary_parts.append("All checks passed.")
    else:
        summary_parts.append(f"Found {failed_checks} violation(s).")
    summary_parts.append(f"Risk level: {risk_level}. Score: {score:.0%}.")
    summary = " ".join(summary_parts)

    return {
        "compliant": compliant,
        "violations": violations,
        "risk_level": risk_level,
        "summary": summary,
        "score": round(score, 2),
        "passed_checks": passed_checks,
        "failed_checks": failed_checks,
    }


# ── Compliance Checker Prompt ────────────────────────────────────────

_COMPLIANCE_SYSTEM_PROMPT = """You are a Compliance Officer in a workflow automation system.
Check the following data against compliance rules:

Data: {data_json}

Compliance Framework: {framework}
Rules: {rules_str}
Strict Mode: {strict_mode}

Produce structured compliance results as JSON matching this schema:
{{
  "compliant": boolean,
  "violations": [
    {{
      "rule": "string — rule identifier",
      "severity": "low|medium|high|critical",
      "description": "string",
      "remediation": "string"
    }}
  ],
  "risk_level": "low|medium|high|critical",
  "summary": "string",
  "score": 0.0-1.0,
  "passed_checks": integer,
  "failed_checks": integer
}}

Assign each violation a severity level and actionable remediation.
Return ONLY valid JSON."""


class ComplianceCheckerNode(WorkflowNode):
    """Checks data against compliance rules and policies.

    Produces structured compliance results with violations, risk levels, and remediation steps.
    Falls back to deterministic mock compliance when no LLM provider is configured.
    """

    type: str = "decision_system.compliance_checker"
    label: str = "Compliance Checker"

    async def execute(self, inputs: dict, ctx: ExecutionContext) -> dict:
        data = inputs.get("data", {})
        rules = inputs.get("rules") or self.config.get("rules", [])
        framework = inputs.get("framework") or self.config.get("framework", "internal")

        if not data:
            return {
                "compliant": True,
                "violations": [],
                "risk_level": "low",
                "summary": "No data to check — nothing to review.",
                "score": 1.0,
                "passed_checks": 0,
                "failed_checks": 0,
            }

        strict_mode = self.config.get("strict_mode", False)

        # Normalize data to dict
        if isinstance(data, list):
            data = {"_items": data}

        rules_str = ", ".join(rules) if rules else "No additional rules specified"

        # Try real provider first
        provider_cfg = ctx.resolve_provider(
            self.config.get("provider"),
            self.config.get("model"),
        )

        fallback_reason = ""

        if provider_cfg:
            provider_config, _ = provider_cfg
            try:
                return await self._llm_compliance(
                    data, framework, rules_str, strict_mode, provider_config
                )
            except Exception as exc:
                fallback_reason = f"{type(exc).__name__}: {exc}"

        # Fake fallback
        result = _generate_fake_compliance(data, framework, strict_mode)
        if fallback_reason:
            result["fallback_reason"] = fallback_reason
        else:
            result["fallback_reason"] = ""
        return result

    async def _llm_compliance(
        self,
        data: dict,
        framework: str,
        rules_str: str,
        strict_mode: bool,
        provider_config: Any,
    ) -> dict:
        """Use LLM to check compliance."""
        client = LLMClient(provider_config)
        data_json = json.dumps(data, default=str)[:3000]

        response = await client.chat_completion(
            messages=[
                {
                    "role": "system",
                    "content": _COMPLIANCE_SYSTEM_PROMPT.format(
                        data_json=data_json,
                        framework=framework,
                        rules_str=rules_str,
                        strict_mode=str(strict_mode),
                    ),
                },
                {
                    "role": "user",
                    "content": f"Check compliance against {framework} framework.",
                },
            ],
            model=provider_config.default_model,
            stream=False,
        )

        result = json.loads(response)

        # Ensure all required fields
        if "compliant" not in result:
            result["compliant"] = False
        if "violations" not in result:
            result["violations"] = []
        if "risk_level" not in result:
            result["risk_level"] = "medium"
        if "summary" not in result:
            result["summary"] = ""
        if "score" not in result:
            result["score"] = 0.0
        if "passed_checks" not in result:
            result["passed_checks"] = 0
        if "failed_checks" not in result:
            result["failed_checks"] = len(result.get("violations", []))
        result["fallback_reason"] = ""

        return result

    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "framework": {
                    "type": "string",
                    "default": "internal",
                    "enum": ["internal", "gdpr", "soc2", "hipaa", "custom"],
                    "title": "Compliance Framework",
                    "description": "Compliance framework to check against",
                },
                "strict_mode": {
                    "type": "boolean",
                    "default": False,
                    "title": "Strict Mode",
                    "description": "Flag borderline items as violations",
                },
                "auto_remediate": {
                    "type": "boolean",
                    "default": False,
                    "title": "Auto Remediate",
                    "description": "Attempt automatic remediation of violations",
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
                    "description": "Data to check for compliance",
                },
                "rules": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Compliance rules to check against",
                },
                "framework": {
                    "type": "string",
                    "description": "Compliance framework (gdpr, soc2, hipaa, internal, custom)",
                },
            },
            "required": ["data"],
        }

    @classmethod
    def get_output_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "compliant": {
                    "type": "boolean",
                    "description": "Overall compliance status",
                },
                "violations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "rule": {"type": "string"},
                            "severity": {
                                "type": "string",
                                "enum": ["low", "medium", "high", "critical"],
                            },
                            "description": {"type": "string"},
                            "remediation": {"type": "string"},
                        },
                    },
                },
                "risk_level": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "critical"],
                },
                "summary": {"type": "string"},
                "score": {"type": "number", "description": "Compliance score (0-1)"},
                "passed_checks": {"type": "integer"},
                "failed_checks": {"type": "integer"},
                "fallback_reason": {"type": "string"},
            },
        }
