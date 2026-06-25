"""Deterministic insight engine for the Agentic Decision System.

v0.4 adds offline, rule-based pattern and vulnerability detection that reads
saved data profiles, local KnowledgeGraph relationships, and CSV files under
``company_data/`` to produce ranked ``Insight`` records.

No real LLM is required or used. All detection logic is deterministic and
testable. Insights are persisted to ``.decision_system/insights/insights.json``.
"""

from __future__ import annotations

from decision_system.insights.models import Insight, InsightCategory, InsightStore, InsightSeverity
from decision_system.insights.store import (
    DEFAULT_INSIGHTS_FILENAME,
    _insights_path,
    load_insights,
    save_insights,
)

__all__ = [
    "Insight",
    "InsightCategory",
    "InsightSeverity",
    "InsightStore",
    "load_insights",
    "save_insights",
]
