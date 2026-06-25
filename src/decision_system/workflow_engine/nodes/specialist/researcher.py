"""ResearcherNode — Retrieves and synthesizes information from connected data sources.

Uses the Phase 5 LLM provider system for AI-powered research synthesis,
with deterministic fake fallback when no provider is configured.
"""

from __future__ import annotations

import json
from typing import Any

from decision_system.workflow_engine.models import ExecutionContext, WorkflowNode
from decision_system.workflow_engine.providers.client import LLMClient

# ── Fake fallback data ─────────────────────────────────────────────────

_MOCK_FINDINGS: dict[str, list[dict[str, Any]]] = {
    "revenue": [
        {
            "statement": "Revenue has grown 15% year-over-year based on available financial data.",
            "citation": "MOCK-FIN-001",
            "confidence": 0.7,
            "source_type": "document",
        },
        {
            "statement": "Operating margins improved by 3 percentage points in the last quarter.",
            "citation": "MOCK-FIN-002",
            "confidence": 0.6,
            "source_type": "document",
        },
    ],
    "risk": [
        {
            "statement": "Risk exposure from market volatility remains elevated, impacting investment returns.",
            "citation": "MOCK-RSK-001",
            "confidence": 0.65,
            "source_type": "document",
        },
        {
            "statement": "Regulatory changes may affect compliance costs in the next fiscal year.",
            "citation": "MOCK-RSK-002",
            "confidence": 0.55,
            "source_type": "data_profile",
        },
    ],
    "growth": [
        {
            "statement": "Customer acquisition costs have decreased 20% due to improved targeting.",
            "citation": "MOCK-GRW-001",
            "confidence": 0.75,
            "source_type": "document",
        },
        {
            "statement": "New market expansion contributed 8% to total revenue growth.",
            "citation": "MOCK-GRW-002",
            "confidence": 0.6,
            "source_type": "graph",
        },
    ],
    "default": [
        {
            "statement": "Sample finding based on available data sources.",
            "citation": "MOCK-DEF-001",
            "confidence": 0.5,
            "source_type": "document",
        },
        {
            "statement": "Additional context found in related documents.",
            "citation": "MOCK-DEF-002",
            "confidence": 0.4,
            "source_type": "document",
        },
    ],
}


def _find_mock_findings(query: str) -> list[dict[str, Any]]:
    """Return deterministic mock findings based on query keywords."""
    query_lower = query.lower()
    for keyword, findings in _MOCK_FINDINGS.items():
        if keyword in query_lower:
            return findings
    return _MOCK_FINDINGS["default"]


# ── Researcher Prompt ─────────────────────────────────────────────────

_RESEARCHER_SYSTEM_PROMPT = """You are a Research Analyst in a workflow automation system.
Given the query "{query}" and the following evidence:

{evidence_snippets}

Produce structured findings as JSON matching this schema:
{{
  "findings": [
    {{
      "statement": "string — factual finding",
      "citation": "string — source reference",
      "confidence": 0.0-1.0,
      "source_type": "document|graph|data_profile|web"
    }}
  ],
  "summary": "string — concise synthesis of findings",
  "gaps": ["string — information gaps or unanswered questions"]
}}

Each finding must cite its source. Flag information gaps in the "gaps" array.
Assign confidence scores based on evidence quality. Return ONLY valid JSON."""


# ── Researcher Node ───────────────────────────────────────────────────


class ResearcherNode(WorkflowNode):
    """Retrieves and synthesizes information from connected data sources.

    Produces structured findings with citations and confidence scores.
    Falls back to deterministic mock data when no LLM provider is configured.
    """

    type: str = "decision_system.researcher"
    label: str = "Researcher"

    async def execute(self, inputs: dict, ctx: ExecutionContext) -> dict:
        query = inputs.get("query", "")
        context = inputs.get("context", "")

        if not query:
            return {
                "findings": [],
                "summary": "No query provided",
                "gaps": ["Missing query"],
                "fallback_reason": "",
            }

        # Try real provider first
        provider_cfg = ctx.resolve_provider(
            self.config.get("provider"),
            self.config.get("model"),
        )

        if provider_cfg is None:
            return self._fake_execute(query)

        return await self._llm_execute(query, context, provider_cfg)

    def _fake_execute(self, query: str) -> dict:
        """Deterministic fake fallback."""
        findings = _find_mock_findings(query)
        return {
            "findings": findings,
            "summary": f"Found {len(findings)} mock findings related to: {query}",
            "gaps": ["Mock data — no real sources consulted"],
            "fallback_reason": "",
        }

    async def _llm_execute(
        self,
        query: str,
        context: str,
        provider_cfg: Any,
    ) -> dict:
        """Execute with real LLM provider."""
        # resolve_provider returns (ProviderConfig, model_name) tuple
        provider_config, resolved_model = provider_cfg
        client = LLMClient(provider_config)

        evidence_snippets = context if context else "No additional context provided."

        try:
            response = await client.chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": _RESEARCHER_SYSTEM_PROMPT.format(
                            query=query,
                            evidence_snippets=evidence_snippets,
                        ),
                    },
                    {"role": "user", "content": f"Research the following: {query}"},
                ],
                model=resolved_model,
                stream=False,
            )

            result = json.loads(response)

            # Ensure all required fields are present
            if "findings" not in result:
                result["findings"] = []
            if "summary" not in result:
                result["summary"] = ""
            if "gaps" not in result:
                result["gaps"] = []
            result["fallback_reason"] = ""
            return result

        except Exception as exc:
            # Fall back to fake on any LLM error
            result = self._fake_execute(query)
            result["fallback_reason"] = f"{type(exc).__name__}: {exc}"
            return result

    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "max_sources": {
                    "type": "integer",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 50,
                    "title": "Max Sources",
                },
                "depth": {
                    "type": "string",
                    "default": "balanced",
                    "enum": ["quick", "balanced", "deep"],
                    "title": "Research Depth",
                },
                "include_graph": {
                    "type": "boolean",
                    "default": False,
                    "title": "Include Knowledge Graph",
                },
                "source_filter": {
                    "type": "string",
                    "default": "all",
                    "enum": ["all", "documents", "graph", "data_profiles"],
                    "title": "Source Filter",
                },
            },
        }

    @classmethod
    def get_input_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Research question or topic",
                },
                "context": {
                    "type": "string",
                    "default": "",
                    "description": "Additional context for the query",
                },
                "source_references": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": [],
                    "description": "Specific document IDs or source labels",
                },
            },
            "required": ["query"],
        }

    @classmethod
    def get_output_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "findings": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "statement": {"type": "string"},
                            "citation": {"type": "string"},
                            "confidence": {
                                "type": "number",
                                "minimum": 0,
                                "maximum": 1,
                            },
                            "source_type": {
                                "type": "string",
                                "enum": ["document", "graph", "data_profile", "web"],
                            },
                        },
                    },
                },
                "summary": {"type": "string"},
                "gaps": {"type": "array", "items": {"type": "string"}},
                "fallback_reason": {"type": "string"},
            },
        }
