"""DecisionSynthesizerNode — Synthesizes multiple evidence streams into weighted decisions.

Takes research findings, analysis, and criteria, then produces ranked
decision options with trade-off analysis and a recommended course of action.
"""

from __future__ import annotations

import copy
import json
from typing import Any

from decision_system.workflow_engine.models import ExecutionContext, WorkflowNode
from decision_system.workflow_engine.providers.client import LLMClient

# ── Fake fallback generators ──────────────────────────────────────────

_FAKE_OPTIONS_BY_KEYWORD: dict[str, list[dict]] = {
    "invest": [
        {
            "title": "Full Investment",
            "description": "Allocate full capital to the opportunity based on positive indicators.",
            "pros": [
                "Maximum upside potential",
                "First-mover advantage",
                "Strong market signal",
            ],
            "cons": [
                "Higher capital at risk",
                "Requires immediate execution",
                "Limited diversification",
            ],
            "confidence": 0.7,
            "criteria_scores": {
                "feasibility": 0.6,
                "impact": 0.8,
                "cost": 0.4,
                "risk": 0.5,
            },
            "risks": [
                {
                    "risk": "Market downturn",
                    "likelihood": "medium",
                    "mitigation": "Phased investment",
                },
                {
                    "risk": "Execution delays",
                    "likelihood": "low",
                    "mitigation": "Dedicated project team",
                },
            ],
        },
        {
            "title": "Phased Investment",
            "description": "Invest in stages, starting with a pilot to validate assumptions.",
            "pros": [
                "Lower initial risk",
                "Option to scale based on results",
                "Learn before committing",
            ],
            "cons": [
                "May miss timing window",
                "Slower to realize returns",
                "Higher total overhead",
            ],
            "confidence": 0.65,
            "criteria_scores": {
                "feasibility": 0.7,
                "impact": 0.6,
                "cost": 0.6,
                "risk": 0.7,
            },
            "risks": [
                {
                    "risk": "Competitor moves first",
                    "likelihood": "medium",
                    "mitigation": "Accelerate phase 1",
                },
            ],
        },
        {
            "title": "Defer Decision",
            "description": "Gather more data before committing capital.",
            "pros": [
                "More information reduces uncertainty",
                "Preserves optionality",
                "No immediate cost",
            ],
            "cons": [
                "May miss opportunity window",
                "Analysis paralysis risk",
                "Delays value creation",
            ],
            "confidence": 0.4,
            "criteria_scores": {
                "feasibility": 0.8,
                "impact": 0.3,
                "cost": 0.9,
                "risk": 0.8,
            },
            "risks": [
                {
                    "risk": "Decision inertia",
                    "likelihood": "medium",
                    "mitigation": "Set a deadline",
                }
            ],
        },
    ],
    "expand": [
        {
            "title": "Aggressive Expansion",
            "description": "Pursue rapid geographic or market expansion.",
            "pros": [
                "Market share growth",
                "Revenue diversification",
                "Competitive moat",
            ],
            "cons": [
                "High capital requirements",
                "Operational complexity",
                "Cultural challenges",
            ],
            "confidence": 0.6,
            "criteria_scores": {
                "feasibility": 0.5,
                "impact": 0.8,
                "cost": 0.3,
                "risk": 0.4,
            },
            "risks": [
                {
                    "risk": "Overextension",
                    "likelihood": "high",
                    "mitigation": "Limit to 2 new markets",
                },
            ],
        },
        {
            "title": "Organic Growth",
            "description": "Focus on deepening existing market presence before expanding.",
            "pros": [
                "Lower risk profile",
                "Builds on existing strengths",
                "Sustainable pace",
            ],
            "cons": [
                "Slower growth trajectory",
                "May miss opportunities",
                "Less differentiation",
            ],
            "confidence": 0.55,
            "criteria_scores": {
                "feasibility": 0.7,
                "impact": 0.5,
                "cost": 0.7,
                "risk": 0.7,
            },
            "risks": [
                {
                    "risk": "Competitive pressure",
                    "likelihood": "medium",
                    "mitigation": "Innovation focus",
                }
            ],
        },
        {
            "title": "Strategic Partnership",
            "description": "Find partners to share costs and risks of expansion.",
            "pros": ["Shared investment", "Local market knowledge", "Reduced risk"],
            "cons": [
                "Profit sharing",
                "Integration complexity",
                "Cultural alignment risk",
            ],
            "confidence": 0.5,
            "criteria_scores": {
                "feasibility": 0.6,
                "impact": 0.6,
                "cost": 0.6,
                "risk": 0.6,
            },
            "risks": [
                {
                    "risk": "Partner misalignment",
                    "likelihood": "medium",
                    "mitigation": "Clear governance agreement",
                },
            ],
        },
    ],
    "expansion": [
        {
            "title": "Aggressive Expansion",
            "description": "Pursue rapid geographic or market expansion.",
            "pros": [
                "Market share growth",
                "Revenue diversification",
                "Competitive moat",
            ],
            "cons": [
                "High capital requirements",
                "Operational complexity",
                "Cultural challenges",
            ],
            "confidence": 0.6,
            "criteria_scores": {
                "feasibility": 0.5,
                "impact": 0.8,
                "cost": 0.3,
                "risk": 0.4,
            },
            "risks": [
                {
                    "risk": "Overextension",
                    "likelihood": "high",
                    "mitigation": "Limit to 2 new markets",
                },
            ],
        },
        {
            "title": "Organic Growth",
            "description": "Focus on deepening existing market presence before expanding.",
            "pros": [
                "Lower risk profile",
                "Builds on existing strengths",
                "Sustainable pace",
            ],
            "cons": [
                "Slower growth trajectory",
                "May miss opportunities",
                "Less differentiation",
            ],
            "confidence": 0.55,
            "criteria_scores": {
                "feasibility": 0.7,
                "impact": 0.5,
                "cost": 0.7,
                "risk": 0.7,
            },
            "risks": [
                {
                    "risk": "Competitive pressure",
                    "likelihood": "medium",
                    "mitigation": "Innovation focus",
                }
            ],
        },
        {
            "title": "Strategic Partnership",
            "description": "Find partners to share costs and risks of expansion.",
            "pros": ["Shared investment", "Local market knowledge", "Reduced risk"],
            "cons": [
                "Profit sharing",
                "Integration complexity",
                "Cultural alignment risk",
            ],
            "confidence": 0.5,
            "criteria_scores": {
                "feasibility": 0.6,
                "impact": 0.6,
                "cost": 0.6,
                "risk": 0.6,
            },
            "risks": [
                {
                    "risk": "Partner misalignment",
                    "likelihood": "medium",
                    "mitigation": "Clear governance agreement",
                },
            ],
        },
    ],
    "default": [
        {
            "title": "Recommended Course",
            "description": "Proceed with the evidence-backed option balancing risk and opportunity.",
            "pros": [
                "Evidence-based approach",
                "Balanced risk profile",
                "Clear execution path",
            ],
            "cons": ["Further analysis may be needed", "Trade-offs accepted"],
            "confidence": 0.5,
            "criteria_scores": {
                "feasibility": 0.6,
                "impact": 0.6,
                "cost": 0.6,
                "risk": 0.6,
            },
            "risks": [
                {
                    "risk": "Unforeseen external factors",
                    "likelihood": "medium",
                    "mitigation": "Regular review cycles",
                },
            ],
        },
        {
            "title": "Alternative Approach",
            "description": "Consider an alternative strategy based on different weighting of criteria.",
            "pros": ["Different risk/reward balance", "May suit specific constraints"],
            "cons": ["Lower overall evidence alignment", "Unknown trade-offs"],
            "confidence": 0.35,
            "criteria_scores": {
                "feasibility": 0.5,
                "impact": 0.5,
                "cost": 0.7,
                "risk": 0.5,
            },
            "risks": [
                {
                    "risk": "Less aligned with evidence",
                    "likelihood": "medium",
                    "mitigation": "Re-evaluate criteria weights",
                }
            ],
        },
        {
            "title": "Do Not Proceed",
            "description": "Hold off until stronger supporting evidence or more favorable conditions emerge.",
            "pros": [
                "Preserves capital",
                "No commitment risk",
                "Maintains flexibility",
            ],
            "cons": [
                "Zero upside potential",
                "May miss opportunities",
                "No strategic progress",
            ],
            "confidence": 0.3,
            "criteria_scores": {
                "feasibility": 0.8,
                "impact": 0.2,
                "cost": 0.9,
                "risk": 0.9,
            },
            "risks": [
                {
                    "risk": "Stagnation",
                    "likelihood": "medium",
                    "mitigation": "Set review date",
                }
            ],
        },
    ],
}


def _fake_options(question: str, criteria: list[dict]) -> list[dict]:
    """Generate deterministic decision options based on question keywords."""
    q_lower = question.lower()
    for keyword, option_list in _FAKE_OPTIONS_BY_KEYWORD.items():
        if keyword in q_lower:
            return copy.deepcopy(option_list)
    return copy.deepcopy(_FAKE_OPTIONS_BY_KEYWORD["default"])


def _default_criteria() -> list[dict]:
    return [
        {"name": "feasibility", "weight": 0.3},
        {"name": "impact", "weight": 0.3},
        {"name": "cost", "weight": 0.2},
        {"name": "risk", "weight": 0.2},
    ]


def _score_options(options: list[dict], criteria: list[dict]) -> tuple[list[dict], dict | None]:
    """Score each option against criteria and determine the best recommendation."""
    weights = {c["name"]: c["weight"] for c in criteria if c.get("weight", 0) > 0}
    total_weight = sum(weights.values())

    scored = []
    for opt in options:
        scores = opt.get("criteria_scores", {})
        if total_weight > 0:
            weighted = sum(scores.get(k, 0) * weights.get(k, 0) for k in weights) / total_weight
        else:
            weighted = 0.5
        scored.append((weighted, opt))

    scored.sort(key=lambda x: x[0], reverse=True)

    if scored:
        best_weighted, best_opt = scored[0]
        recommendation = {
            "title": best_opt["title"],
            "rationale": f"Highest weighted score ({best_weighted:.2f}) across criteria.",
            "overall_confidence": best_opt.get("confidence", 0.5) * 0.8 + best_weighted * 0.2,
        }
    else:
        recommendation = None

    return [opt for _, opt in scored], recommendation


# ── Synthesizer Prompt ───────────────────────────────────────────────

_SYNTHESIZER_SYSTEM_PROMPT = """You are a Decision Synthesis specialist in a workflow automation system.
Given the question "{question}" and the following evidence:

{evidence_context}

And the following decision criteria:
{criteria_text}

Generate {num_options} distinct decision options. Each option should include:
- Title and description
- Pros and cons (3-5 each)
- Confidence score (0-1)
- Scores against each criterion (0-1)
- Risk assessments (if enabled)

Return JSON matching this schema:
{{
  "options": [
    {{
      "title": "string",
      "description": "string",
      "pros": ["string"],
      "cons": ["string"],
      "confidence": 0.0-1.0,
      "criteria_scores": {{"criterion_name": 0.0-1.0}},
      "risks": [
        {{
          "risk": "string",
          "likelihood": "low|medium|high",
          "mitigation": "string"
        }}
      ]
    }}
  ],
  "recommendation": {{
    "title": "string",
    "rationale": "string",
    "overall_confidence": 0.0-1.0
  }},
  "trade_offs_summary": "string"
}}

Score each option against every criterion. Indicate the recommended option
in the recommendation field. Return ONLY valid JSON."""


class SynthesizerNode(WorkflowNode):
    """Synthesizes multiple evidence/analysis streams into weighted decisions.

    Produces ranked decision options with trade-off analysis, risk assessment,
    and a recommended course of action.
    """

    type: str = "decision_system.synthesizer"
    label: str = "Decision Synthesizer"

    async def execute(self, inputs: dict, ctx: ExecutionContext) -> dict:
        question = inputs.get("question", "") or inputs.get("query", "")
        evidence_streams = inputs.get("evidence_streams", [])
        criteria = inputs.get("criteria", _default_criteria())

        # Auto-detect upstream outputs when connected via default DAG port
        if not evidence_streams:
            # Check for Researcher-style findings at the top level
            raw_findings = inputs.get("findings")
            if raw_findings and isinstance(raw_findings, list) and len(raw_findings) > 0:
                evidence_streams = [
                    {
                        "source_label": "Research Findings",
                        "content": {"findings": raw_findings},
                    },
                ]
            # Check for another Synthesizer's options
            elif (
                inputs.get("options")
                and isinstance(inputs.get("options"), list)
                and len(inputs.get("options")) > 0
            ):
                evidence_streams = [
                    {
                        "source_label": "Prior Synthesis",
                        "content": {"options": inputs["options"]},
                    },
                ]
            # Check for report text
            elif inputs.get("report") or inputs.get("text"):
                evidence_streams = [
                    {
                        "source_label": "Report",
                        "content": {"text": inputs.get("report") or inputs.get("text", "")},
                    },
                ]

        if not question:
            return {
                "options": [],
                "recommendation": None,
                "trade_offs_summary": "No question provided — cannot synthesize.",
                "fallback_reason": "",
            }

        if not evidence_streams:
            # Single option based on question alone
            options, recommendation = _score_options(
                [
                    {
                        "title": "Preliminary Assessment",
                        "description": f"Assessment based on: {question}",
                        "pros": ["Based on available information"],
                        "cons": ["No evidence streams provided — consider adding upstream sources"],
                        "confidence": 0.2,
                        "criteria_scores": {c["name"]: 0.5 for c in criteria},
                        "risks": [
                            {
                                "risk": "Insufficient evidence",
                                "likelihood": "high",
                                "mitigation": "Add upstream analysis nodes",
                            }
                        ],
                    }
                ],
                criteria,
            )
            return {
                "options": options,
                "recommendation": recommendation,
                "trade_offs_summary": "No evidence provided — single preliminary option generated.",
                "fallback_reason": "",
            }

        # Build context from evidence streams
        context_parts = []
        for stream in evidence_streams:
            label = stream.get("source_label", "Unlabeled source")
            content = stream.get("content", {})
            context_parts.append(f"[{label}]: {json.dumps(content, indent=2)}")
        evidence_context = "\n\n".join(context_parts)

        # Try real provider first
        provider_cfg = ctx.resolve_provider(
            self.config.get("provider"),
            self.config.get("model"),
        )

        if provider_cfg and evidence_streams:
            provider_config, _ = provider_cfg
            try:
                return await self._llm_synthesize(
                    question, evidence_context, criteria, provider_config
                )
            except Exception as exc:
                fallback_reason = f"{type(exc).__name__}: {exc}"
                # Fall through to fake
        else:
            fallback_reason = ""

        # Fake fallback
        options = _fake_options(question, criteria)
        options, recommendation = _score_options(options, criteria)

        include_risks = self.config.get("include_risks", True)
        if not include_risks:
            for opt in options:
                opt.pop("risks", None)

        trade_offs = f"Generated {len(options)} options based on keyword analysis of: {question}"

        return {
            "options": options,
            "recommendation": recommendation,
            "trade_offs_summary": trade_offs,
            "fallback_reason": fallback_reason,
        }

    async def _llm_synthesize(
        self,
        question: str,
        evidence_context: str,
        criteria: list[dict],
        provider_config: Any,
    ) -> dict:
        """Use LLM to generate decision options."""
        client = LLMClient(provider_config)
        max_options = self.config.get("max_options", 5)
        include_risks = self.config.get("include_risks", True)
        criteria_text = json.dumps(criteria, indent=2)

        response = await client.chat_completion(
            messages=[
                {
                    "role": "system",
                    "content": _SYNTHESIZER_SYSTEM_PROMPT.format(
                        question=question,
                        evidence_context=evidence_context,
                        criteria_text=criteria_text,
                        num_options=max_options,
                    ),
                },
                {"role": "user", "content": f"Synthesize decisions for: {question}"},
            ],
            model=provider_config.default_model,
            stream=False,
        )

        result = json.loads(response)

        # Ensure all required fields
        if "options" not in result:
            result["options"] = []
        if "recommendation" not in result:
            result["recommendation"] = None
        if "trade_offs_summary" not in result:
            result["trade_offs_summary"] = ""
        if "fallback_reason" not in result:
            result["fallback_reason"] = ""

        # Apply risk filter if disabled
        if not include_risks:
            for opt in result["options"]:
                opt.pop("risks", None)

        return result

    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "decision_framework": {
                    "type": "string",
                    "default": "weighted_matrix",
                    "enum": ["pros_cons", "weighted_matrix", "tiered_recommendation"],
                    "title": "Decision Framework",
                },
                "max_options": {
                    "type": "integer",
                    "default": 5,
                    "minimum": 2,
                    "maximum": 10,
                    "title": "Max Options",
                },
                "include_risks": {
                    "type": "boolean",
                    "default": True,
                    "title": "Include Risk Assessments",
                },
            },
        }

    @classmethod
    def get_input_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "Decision question to synthesize",
                },
                "evidence_streams": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "source_label": {"type": "string"},
                            "content": {"type": "object"},
                        },
                    },
                    "description": "Multiple evidence/analysis streams to synthesize",
                },
                "criteria": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "weight": {"type": "number", "minimum": 0, "maximum": 1},
                        },
                    },
                    "description": "Decision criteria with weights",
                },
            },
            "required": ["question"],
        }

    @classmethod
    def get_output_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "options": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "description": {"type": "string"},
                            "pros": {"type": "array", "items": {"type": "string"}},
                            "cons": {"type": "array", "items": {"type": "string"}},
                            "confidence": {
                                "type": "number",
                                "minimum": 0,
                                "maximum": 1,
                            },
                            "criteria_scores": {"type": "object"},
                            "risks": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "risk": {"type": "string"},
                                        "likelihood": {
                                            "type": "string",
                                            "enum": ["low", "medium", "high"],
                                        },
                                        "mitigation": {"type": "string"},
                                    },
                                },
                            },
                        },
                    },
                },
                "recommendation": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "rationale": {"type": "string"},
                        "overall_confidence": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 1,
                        },
                    },
                },
                "trade_offs_summary": {"type": "string"},
                "fallback_reason": {"type": "string"},
            },
        }
