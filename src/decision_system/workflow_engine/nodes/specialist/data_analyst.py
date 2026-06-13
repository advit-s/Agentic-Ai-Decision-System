"""DataAnalystNode — Analyzes structured data for trends, anomalies, and correlations.

Accepts array-of-objects data (CSV rows, JSON records) and produces
structured analysis using LLM when available or deterministic rules as fake fallback.
"""

from __future__ import annotations

import json
from typing import Any

from decision_system.workflow_engine.models import WorkflowNode, ExecutionContext
from decision_system.workflow_engine.providers.client import LLMClient


# ── Fake fallback generators ─────────────────────────────────────────

_MOCK_PROFILE = {
    "row_count": 150,
    "column_count": 8,
    "numeric_columns": {
        "revenue": {"min": 10000, "max": 500000, "mean": 185000, "median": 150000, "std": 45000},
        "cost": {"min": 5000, "max": 300000, "mean": 95000, "median": 80000, "std": 28000},
        "count": {"min": 1, "max": 500, "mean": 45, "median": 30, "std": 22},
    },
    "categorical_columns": {
        "region": {"top_values": [("North", 45), ("South", 38), ("East", 35), ("West", 32)]},
        "status": {"top_values": [("active", 100), ("pending", 30), ("completed", 20)]},
    },
    "missing_values": {
        "revenue": {"count": 2, "pct": 1.3},
        "region": {"count": 5, "pct": 3.3},
    },
    "data_quality_notes": ["2 missing revenue values (1.3%)", "5 missing region values (3.3%)"],
}

_MOCK_TREND = {
    "overall_direction": "upward",
    "confidence": 0.72,
    "trends": [
        {"column": "revenue", "direction": "up", "magnitude": "strong", "period": "monthly", "pct_change": 15.2},
        {"column": "cost", "direction": "up", "magnitude": "moderate", "period": "monthly", "pct_change": 8.1},
        {"column": "count", "direction": "down", "magnitude": "weak", "period": "monthly", "pct_change": -2.3},
    ],
    "seasonal_patterns": ["Revenue shows Q4 spikes consistent with holiday seasonality"],
}

_MOCK_ANOMALY = {
    "total_outliers": 3,
    "outliers": [
        {"column": "revenue", "row": 42, "value": 520000, "expected_range": "10000-350000", "severity": "high", "description": "Revenue spike 48% above normal range"},
        {"column": "cost", "row": 88, "value": 4500, "expected_range": "5000-200000", "severity": "medium", "description": "Cost drop below minimum threshold"},
        {"column": "count", "row": 15, "value": 520, "expected_range": "1-400", "severity": "low", "description": "Count exceeds typical maximum"},
    ],
    "anomaly_score": 0.08,
}

_MOCK_CORRELATION = {
    "pairs": [
        {"columns": ["revenue", "cost"], "coefficient": 0.82, "strength": "strong", "relationship": "positive — higher revenue correlates with higher costs"},
        {"columns": ["revenue", "count"], "coefficient": 0.45, "strength": "moderate", "relationship": "positive — more transactions increase revenue"},
        {"columns": ["cost", "count"], "coefficient": 0.31, "strength": "weak", "relationship": "weak positive correlation"},
    ],
    "notable_insights": ["revenue vs cost (0.82) — strongest correlation in dataset"],
}

_MOCK_SUMMARY = {
    "profile_summary": {
        "rows": 150,
        "columns": 8,
        "numeric_count": 3,
        "categorical_count": 2,
        "missing_pct": 2.1,
    },
    "key_findings": [
        "Revenue averages $185K with significant variation (std $45K)",
        "North region has the most records (45)",
        "Cost/revenue ratio suggests healthy margins",
        "2.1% of data has missing values — acceptable for analysis",
    ],
    "recommendation": "Data quality is good. Consider drilling into North region performance for optimization opportunities.",
}


def _fake_analysis(data: list | dict, analysis_type: str) -> dict:
    """Generate deterministic mock analysis based on analysis type."""
    data_row_count = len(data) if isinstance(data, list) else 1
    analysis_type_lower = analysis_type.lower()

    if "profile" in analysis_type_lower:
        result = dict(_MOCK_PROFILE)
        result["_note"] = f"Mock profile for {data_row_count} rows of data"
        return result
    elif "trend" in analysis_type_lower:
        result = dict(_MOCK_TREND)
        # Scale confidence based on data size
        result["confidence"] = min(0.9, data_row_count / 200)
        result["_note"] = f"Mock trend analysis for {data_row_count} rows"
        return result
    elif "anomaly" in analysis_type_lower:
        result = dict(_MOCK_ANOMALY)
        result["_note"] = f"Mock anomaly detection for {data_row_count} rows"
        return result
    elif "correlation" in analysis_type_lower:
        result = dict(_MOCK_CORRELATION)
        result["_note"] = f"Mock correlation analysis for {data_row_count} rows"
        return result
    else:
        result = dict(_MOCK_SUMMARY)
        result["_note"] = f"Mock summary for {data_row_count} rows"
        return result


def _summarize_analysis(analysis: dict, analysis_type: str) -> str:
    """Generate a human-readable summary from mock analysis results."""
    type_lower = analysis_type.lower()
    if "profile" in type_lower:
        return f"Profiled {analysis.get('row_count', 'N/A')} rows across {analysis.get('column_count', 'N/A')} columns. {analysis.get('data_quality_notes', ['No issues'])[0]}"
    elif "trend" in type_lower:
        direction = analysis.get("overall_direction", "unknown")
        trends = analysis.get("trends", [])
        return f"Overall trend: {direction}. Found {len(trends)} column-level trends with {analysis.get('confidence', 0):.0%} confidence."
    elif "anomaly" in type_lower:
        n = analysis.get("total_outliers", 0)
        return f"Detected {n} outlier(s). Anomaly score: {analysis.get('anomaly_score', 0):.2f} (lower is more normal)."
    elif "correlation" in type_lower:
        pairs = analysis.get("pairs", [])
        top = pairs[0] if pairs else {}
        cols = " & ".join(top.get("columns", []))
        return f"Found {len(pairs)} correlations. Strongest: {cols} ({top.get('coefficient', 0):.2f}, {top.get('strength', 'unknown')})."
    else:
        findings = analysis.get("key_findings", [])
        return f"Analysis complete. {len(findings)} key findings. {findings[0] if findings else ''}"


# ── Data Analyst Prompt ──────────────────────────────────────────────

_DATA_ANALYST_SYSTEM_PROMPT = """You are a Data Analyst in a workflow automation system.
Analyze the following structured data:

{data_json}

Analysis type: {analysis_type}
{column_focus}

Return JSON matching this schema:
{{
  "analysis": {{
    ... analysis-specific structure ...
  }},
  "summary": "string — human-readable summary of findings",
  "charts": {{ ... chart-friendly data if applicable ... }}
}}

For "profile" analysis: include row count, column stats, missing values, data quality notes.
For "trend" analysis: identify upward/downward patterns, magnitudes, periods.
For "anomaly" analysis: detect outliers with severity, expected range, descriptions.
For "correlation" analysis: compute pairwise correlations with strength descriptions.
For "summary" analysis: provide key findings and a recommendation.

Return ONLY valid JSON."""


class DataAnalystNode(WorkflowNode):
    """Analyzes structured data for trends, anomalies, and correlations.

    Accepts array-of-objects data and produces structured analysis
    using LLM when available or deterministic rules as fake fallback.
    """
    type: str = "decision_system.data_analyst"
    label: str = "Data Analyst"

    async def execute(self, inputs: dict, ctx: ExecutionContext) -> dict:
        data = inputs.get("data", [])
        analysis_type = inputs.get("analysis_type") or self.config.get("analysis_type", "summary")
        columns = inputs.get("columns") or self.config.get("columns", [])

        if not data:
            return {
                "analysis": {},
                "summary": "No data provided — nothing to analyze.",
                "charts": {},
                "fallback_reason": "",
            }

        # Normalize data: if it's a dict, wrap in list
        if isinstance(data, dict):
            data = [data]

        column_focus = f"Focus on columns: {', '.join(columns)}" if columns else "Analyze all available columns."

        # Try real provider first
        provider_cfg = ctx.resolve_provider(
            self.config.get("provider"),
            self.config.get("model"),
        )

        fallback_reason = ""

        if provider_cfg:
            provider_config, _ = provider_cfg
            try:
                return await self._llm_analyze(data, analysis_type, column_focus, provider_config)
            except Exception as exc:
                fallback_reason = f"{type(exc).__name__}: {exc}"

        # Fake fallback
        analysis = _fake_analysis(data, analysis_type)
        summary = _summarize_analysis(analysis, analysis_type)

        return {
            "analysis": analysis,
            "summary": summary,
            "charts": {},
            "fallback_reason": fallback_reason,
        }

    async def _llm_analyze(
        self, data: list, analysis_type: str, column_focus: str, provider_config: Any,
    ) -> dict:
        """Use LLM to analyze structured data."""
        client = LLMClient(provider_config)

        # Sample data to avoid token limits
        max_rows = self.config.get("max_rows", 1000)
        sample = data[:max_rows]
        data_json = json.dumps(sample[:50]) if len(sample) > 50 else json.dumps(sample)
        if len(sample) > 50:
            data_json += f"\n... and {len(sample) - 50} more rows."

        response = await client.chat_completion(
            messages=[
                {"role": "system", "content": _DATA_ANALYST_SYSTEM_PROMPT.format(
                    data_json=data_json,
                    analysis_type=analysis_type,
                    column_focus=column_focus,
                )},
                {"role": "user", "content": f"Analyze this data ({len(sample)} rows) with type: {analysis_type}."},
            ],
            model=provider_config.default_model,
            stream=False,
        )

        result = json.loads(response)

        # Ensure all required fields
        if "analysis" not in result:
            result["analysis"] = {}
        if "summary" not in result:
            result["summary"] = ""
        if "charts" not in result:
            result["charts"] = {}
        if "fallback_reason" not in result:
            result["fallback_reason"] = ""

        return result

    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "analysis_type": {
                    "type": "string",
                    "default": "summary",
                    "enum": ["profile", "summary", "trend", "anomaly", "correlation"],
                    "title": "Analysis Type",
                    "description": "Type of data analysis to perform",
                },
                "max_rows": {
                    "type": "integer", "default": 1000, "minimum": 1, "maximum": 100000,
                    "title": "Max Rows",
                    "description": "Maximum rows to analyze",
                },
                "include_charts": {
                    "type": "boolean", "default": False,
                    "title": "Include Chart Data",
                },
            },
        }

    @classmethod
    def get_input_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "data": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Array of data records (objects) to analyze",
                },
                "analysis_type": {
                    "type": "string",
                    "default": "summary",
                    "enum": ["profile", "summary", "trend", "anomaly", "correlation"],
                    "description": "Override config analysis type for this execution",
                },
                "columns": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific columns to analyze (optional)",
                },
            },
            "required": ["data"],
        }

    @classmethod
    def get_output_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "analysis": {"type": "object", "description": "Structured analysis results"},
                "summary": {"type": "string", "description": "Human-readable analysis summary"},
                "charts": {"type": "object", "description": "Chart-friendly data (optional)"},
                "fallback_reason": {"type": "string"},
            },
        }
