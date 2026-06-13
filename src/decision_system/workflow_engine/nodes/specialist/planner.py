"""PlannerNode — Generates step-by-step execution plans from goals.

Uses the Phase 5 LLM provider system for AI-powered planning,
with deterministic fake fallback when no provider is configured.
"""

from __future__ import annotations

import json
from typing import Any

from decision_system.workflow_engine.models import WorkflowNode, ExecutionContext
from decision_system.workflow_engine.providers.client import LLMClient


# ── Fake fallback generators ─────────────────────────────────────────


def _generate_fake_plan(goal: str, detail_level: str, max_steps: int) -> dict:
    """Generate deterministic mock plan based on goal keywords."""
    goal_lower = goal.lower()
    steps: list[dict[str, Any]] = []

    if any(kw in goal_lower for kw in ("invest", "budget", "cost")):
        # Financial planning plan
        steps = [
            {"step_number": 1, "title": "Assess Current Financial Position", "description": "Review cash flow, balance sheet, and P&L statements to establish baseline.", "estimated_effort": "3 days", "dependencies": []},
            {"step_number": 2, "title": "Define Investment Objectives", "description": "Clarify short-term and long-term financial goals, risk tolerance, and return expectations.", "estimated_effort": "1 day", "dependencies": [1]},
            {"step_number": 3, "title": "Research Investment Options", "description": "Evaluate available investment vehicles, historical performance, and market conditions.", "estimated_effort": "5 days", "dependencies": [2]},
            {"step_number": 4, "title": "Develop Budget Allocation", "description": "Allocate capital across selected investments with diversification strategy.", "estimated_effort": "2 days", "dependencies": [3]},
            {"step_number": 5, "title": "Implement Investment Plan", "description": "Execute purchases, set up monitoring, and document the investment plan.", "estimated_effort": "2 days", "dependencies": [4]},
            {"step_number": 6, "title": "Establish Review Cadence", "description": "Set up periodic performance reviews and rebalancing triggers.", "estimated_effort": "1 day", "dependencies": [5]},
        ]
        summary = "Financial planning and investment strategy"
    elif any(kw in goal_lower for kw in ("migrate", "deploy", "launch")):
        # Technical project plan
        steps = [
            {"step_number": 1, "title": "Requirements Gathering", "description": "Document technical requirements, constraints, and success criteria.", "estimated_effort": "3 days", "dependencies": []},
            {"step_number": 2, "title": "Architecture Design", "description": "Design system architecture, select technology stack, and create migration/deployment blueprint.", "estimated_effort": "5 days", "dependencies": [1]},
            {"step_number": 3, "title": "Environment Setup", "description": "Provision development, staging, and production environments.", "estimated_effort": "2 days", "dependencies": [2]},
            {"step_number": 4, "title": "Implementation", "description": "Build and configure the solution according to architecture design.", "estimated_effort": "15 days", "dependencies": [3]},
            {"step_number": 5, "title": "Testing & Validation", "description": "Run unit, integration, and user acceptance tests.", "estimated_effort": "5 days", "dependencies": [4]},
            {"step_number": 6, "title": "Deployment & Go-Live", "description": "Deploy to production, verify functionality, and monitor initial performance.", "estimated_effort": "2 days", "dependencies": [5]},
        ]
        summary = "Technical project plan for migration, deployment, or launch"
    elif any(kw in goal_lower for kw in ("research", "analyze", "study")):
        # Research methodology plan
        steps = [
            {"step_number": 1, "title": "Literature Review", "description": "Survey existing research, publications, and related work in the domain.", "estimated_effort": "7 days", "dependencies": []},
            {"step_number": 2, "title": "Define Research Questions", "description": "Formulate clear, testable hypotheses and research questions.", "estimated_effort": "2 days", "dependencies": [1]},
            {"step_number": 3, "title": "Design Methodology", "description": "Select research methods, data collection techniques, and analysis framework.", "estimated_effort": "3 days", "dependencies": [2]},
            {"step_number": 4, "title": "Data Collection", "description": "Gather data according to the methodology, ensuring quality and completeness.", "estimated_effort": "10 days", "dependencies": [3]},
            {"step_number": 5, "title": "Data Analysis", "description": "Process and analyze collected data using selected techniques.", "estimated_effort": "7 days", "dependencies": [4]},
            {"step_number": 6, "title": "Interpretation & Reporting", "description": "Interpret findings, draw conclusions, and prepare research report.", "estimated_effort": "5 days", "dependencies": [5]},
        ]
        summary = "Research methodology and analysis plan"
    else:
        # Generic project plan
        steps = [
            {"step_number": 1, "title": "Define Scope & Objectives", "description": "Clearly define project scope, objectives, deliverables, and success criteria.", "estimated_effort": "2 days", "dependencies": []},
            {"step_number": 2, "title": "Resource Planning", "description": "Identify required resources, team members, tools, and budget.", "estimated_effort": "2 days", "dependencies": [1]},
            {"step_number": 3, "title": "Create Work Breakdown", "description": "Break the work into manageable tasks and milestones.", "estimated_effort": "3 days", "dependencies": [2]},
            {"step_number": 4, "title": "Execution", "description": "Execute tasks according to the plan, tracking progress against milestones.", "estimated_effort": "20 days", "dependencies": [3]},
            {"step_number": 5, "title": "Review & Adjust", "description": "Review outcomes against objectives, adjust approach as needed.", "estimated_effort": "2 days", "dependencies": [4]},
        ]
        summary = "Generic project execution plan"

    # Trim to max_steps
    steps = steps[:max_steps]

    # Estimate duration based on steps
    total_days = sum(
        int(s["estimated_effort"].split()[0]) for s in steps
        if s["estimated_effort"].split()[0].isdigit()
    )
    estimated_duration = f"{total_days} days"

    return {
        "plan": steps,
        "summary": summary,
        "total_steps": len(steps),
        "estimated_duration": estimated_duration,
    }


# ── Planner Prompt ──────────────────────────────────────────────────

_PLANNER_SYSTEM_PROMPT = """You are a Strategic Planner in a workflow automation system.
Given the following goal and context:

Goal: {goal}
Constraints: {constraints}
Context: {context}
Detail Level: {detail_level}
Max Steps: {max_steps}

Produce a structured plan as JSON matching this schema:
{{
  "plan": [
    {{
      "step_number": integer,
      "title": "string",
      "description": "string",
      "estimated_effort": "string (e.g. '3 days')",
      "dependencies": [integer step_numbers that this step depends on]
    }}
  ],
  "summary": "string — one-line plan summary",
  "total_steps": integer,
  "estimated_duration": "string"
}}

Each step must have a clear description, effort estimate, and dependency references.
Return ONLY valid JSON."""


class PlannerNode(WorkflowNode):
    """Generates step-by-step execution plans from goals.

    Produces structured plans with numbered steps, dependencies, and effort estimates.
    Falls back to deterministic fake plan when no LLM provider is configured.
    """
    type: str = "decision_system.planner"
    label: str = "Planner"

    async def execute(self, inputs: dict, ctx: ExecutionContext) -> dict:
        goal = inputs.get("goal", "")
        constraints = inputs.get("constraints", "")
        context = inputs.get("context", "")

        if not goal:
            return {
                "plan": [],
                "summary": "No goal provided — nothing to plan.",
                "total_steps": 0,
                "estimated_duration": "0 days",
            }

        detail_level = self.config.get("detail_level", "detailed")
        max_steps = min(self.config.get("max_steps", 8), 20)

        # Try real provider first
        provider_cfg = ctx.resolve_provider(
            self.config.get("provider"),
            self.config.get("model"),
        )

        fallback_reason = ""

        if provider_cfg:
            provider_config, _ = provider_cfg
            try:
                return await self._llm_plan(goal, constraints, context, detail_level, max_steps, provider_config)
            except Exception as exc:
                fallback_reason = f"{type(exc).__name__}: {exc}"

        # Fake fallback
        result = _generate_fake_plan(goal, detail_level, max_steps)
        if fallback_reason:
            result["fallback_reason"] = fallback_reason
        else:
            result["fallback_reason"] = ""
        return result

    async def _llm_plan(
        self, goal: str, constraints: str, context: str,
        detail_level: str, max_steps: int, provider_config: Any,
    ) -> dict:
        """Use LLM to generate a structured plan."""
        client = LLMClient(provider_config)

        response = await client.chat_completion(
            messages=[
                {"role": "system", "content": _PLANNER_SYSTEM_PROMPT.format(
                    goal=goal,
                    constraints=constraints or "None specified",
                    context=context or "None provided",
                    detail_level=detail_level,
                    max_steps=max_steps,
                )},
                {"role": "user", "content": f"Generate a {detail_level} plan for: {goal}"},
            ],
            model=provider_config.default_model,
            stream=False,
        )

        result = json.loads(response)

        # Ensure all required fields
        if "plan" not in result:
            result["plan"] = []
        if "summary" not in result:
            result["summary"] = ""
        if "total_steps" not in result:
            result["total_steps"] = len(result.get("plan", []))
        if "estimated_duration" not in result:
            result["estimated_duration"] = ""
        result["fallback_reason"] = ""

        return result

    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "detail_level": {
                    "type": "string",
                    "default": "detailed",
                    "enum": ["high_level", "detailed", "very_detailed"],
                    "title": "Detail Level",
                    "description": "Level of detail in the generated plan",
                },
                "include_timeline": {
                    "type": "boolean",
                    "default": True,
                    "title": "Include Timeline",
                },
                "max_steps": {
                    "type": "integer",
                    "default": 8,
                    "minimum": 2,
                    "maximum": 20,
                    "title": "Max Steps",
                    "description": "Maximum number of plan steps",
                },
            },
        }

    @classmethod
    def get_input_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "goal": {
                    "type": "string",
                    "description": "The objective to plan for",
                },
                "constraints": {
                    "type": "string",
                    "default": "",
                    "description": "Constraints or requirements",
                },
                "context": {
                    "type": "string",
                    "default": "",
                    "description": "Additional context",
                },
            },
            "required": ["goal"],
        }

    @classmethod
    def get_output_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "plan": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "step_number": {"type": "integer"},
                            "title": {"type": "string"},
                            "description": {"type": "string"},
                            "estimated_effort": {"type": "string"},
                            "dependencies": {"type": "array", "items": {"type": "integer"}},
                        },
                    },
                    "description": "Ordered list of plan steps",
                },
                "summary": {"type": "string", "description": "One-line plan summary"},
                "total_steps": {"type": "integer", "description": "Number of steps in the plan"},
                "estimated_duration": {"type": "string", "description": "Estimated total duration"},
                "fallback_reason": {"type": "string"},
            },
        }
