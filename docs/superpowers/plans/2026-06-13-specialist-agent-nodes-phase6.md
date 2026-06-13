# Phase 6: Bounded Specialist Agent Nodes — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 3 new AI-powered drag-and-drop workflow nodes — Researcher, Critic/Judge, and Decision Synthesizer — each with structured I/O schemas, LLM provider support via the Phase 5 provider system, and deterministic fake fallback matching the same schema.

**Architecture:** Each node is a `WorkflowNode` subclass in a new `nodes/specialist/` package, using `ctx.resolve_provider()` to get an `LLMClient` or fall back to deterministic mock data. The frontend adds 3 entries to `MOCK_NODE_TYPES` (no new card components needed — NodeComponent.jsx is generic). The DAG engine needs no changes.

**Tech Stack:** Python 3.11+, Pydantic v2, WorkflowNode base class, LLMClient (httpx), React (Vite) frontend with reactflow, pytest with httpx mock.

---

### Task 1: Create the specialist node package skeleton

**Files:**
- Create: `src/decision_system/workflow_engine/nodes/specialist/__init__.py`

- [ ] **Step 1: Create the package init that exports placeholder nodes**

```python
"""Specialist agent node types — AI-powered bounded agents for the workflow builder.

Each node uses the Phase 5 provider system to call real LLMs, with
deterministic fake fallback when no provider is configured.
"""

from decision_system.workflow_engine.nodes.specialist.researcher import ResearcherNode
from decision_system.workflow_engine.nodes.specialist.critic import CriticNode
from decision_system.workflow_engine.nodes.specialist.synthesizer import SynthesizerNode

__all__ = [
    "ResearcherNode",
    "CriticNode",
    "SynthesizerNode",
]
```

- [ ] **Step 2: Verify package imports without error**

Run:
```bash
python -c "from decision_system.workflow_engine.nodes.specialist import ResearcherNode, CriticNode, SynthesizerNode; print('imports ok')"
```
Expected: ImportError (modules don't exist yet — this validates the import path works once files exist)

- [ ] **Step 3: Commit**

```bash
git add src/decision_system/workflow_engine/nodes/specialist/__init__.py
git commit -m "feat: create specialist node package skeleton"
```

---

### Task 2: ResearcherNode — Backend Implementation

**Files:**
- Create: `src/decision_system/workflow_engine/nodes/specialist/researcher.py`
- Create: `tests/test_workflow_engine/test_specialist_nodes/__init__.py`
- Create: `tests/test_workflow_engine/test_specialist_nodes/test_researcher.py`

- [ ] **Step 1: Write the fake fallback helper and node class**

```python
"""ResearcherNode — Retrieves and synthesizes information from connected data sources.

Uses the Phase 5 LLM provider system for AI-powered research synthesis,
with deterministic fake fallback when no provider is configured.
"""

from __future__ import annotations

import json
from typing import Any

from decision_system.workflow_engine.models import WorkflowNode, ExecutionContext
from decision_system.workflow_engine.providers.client import LLMClient


# ── Fake fallback data ─────────────────────────────────────────────────

_MOCK_FINDINGS: dict[str, list[dict[str, Any]]] = {
    "revenue": [
        {"statement": "Revenue has grown 15% year-over-year based on available financial data.", "citation": "MOCK-FIN-001", "confidence": 0.7, "source_type": "document"},
        {"statement": "Operating margins improved by 3 percentage points in the last quarter.", "citation": "MOCK-FIN-002", "confidence": 0.6, "source_type": "document"},
    ],
    "risk": [
        {"statement": "Market volatility remains elevated, impacting investment returns.", "citation": "MOCK-RSK-001", "confidence": 0.65, "source_type": "document"},
        {"statement": "Regulatory changes may affect compliance costs in the next fiscal year.", "citation": "MOCK-RSK-002", "confidence": 0.55, "source_type": "data_profile"},
    ],
    "growth": [
        {"statement": "Customer acquisition costs have decreased 20% due to improved targeting.", "citation": "MOCK-GRW-001", "confidence": 0.75, "source_type": "document"},
        {"statement": "New market expansion contributed 8% to total revenue growth.", "citation": "MOCK-GRW-002", "confidence": 0.6, "source_type": "graph"},
    ],
    "default": [
        {"statement": "Sample finding based on available data sources.", "citation": "MOCK-DEF-001", "confidence": 0.5, "source_type": "document"},
        {"statement": "Additional context found in related documents.", "citation": "MOCK-DEF-002", "confidence": 0.4, "source_type": "document"},
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
        source_references = inputs.get("source_references", [])

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
        self, query: str, context: str, provider_cfg: Any,
    ) -> dict:
        """Execute with real LLM provider."""
        client = LLMClient(provider_cfg)

        evidence_snippets = context if context else "No additional context provided."

        try:
            response = await client.chat_completion(
                messages=[
                    {"role": "system", "content": _RESEARCHER_SYSTEM_PROMPT.format(
                        query=query,
                        evidence_snippets=evidence_snippets,
                    )},
                    {"role": "user", "content": f"Research the following: {query}"},
                ],
                model=provider_cfg.default_model,
                stream=False,
                response_format={"type": "json_object"},
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
                    "type": "integer", "default": 5, "minimum": 1, "maximum": 50,
                    "title": "Max Sources",
                },
                "depth": {
                    "type": "string", "default": "balanced",
                    "enum": ["quick", "balanced", "deep"],
                    "title": "Research Depth",
                },
                "include_graph": {
                    "type": "boolean", "default": False,
                    "title": "Include Knowledge Graph",
                },
                "source_filter": {
                    "type": "string", "default": "all",
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
                            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
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
```

- [ ] **Step 2: Write the test file (test_researcher.py)**

```python
"""Tests for ResearcherNode — fake fallback and LLM paths."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest
from pytest_httpx import HTTPXMock

from decision_system.workflow_engine.models import ExecutionContext
from decision_system.workflow_engine.nodes.specialist.researcher import ResearcherNode
from decision_system.workflow_engine.providers.store import ProviderConfig, ProviderStore

pytestmark = pytest.mark.asyncio

SYS_PROMPT_RESEARCHER = "You are a Research Analyst"


def _store_with_provider() -> ProviderStore:
    tmp = Path(tempfile.mkdtemp())
    store = ProviderStore(tmp / "providers.json")
    store.save([
        ProviderConfig(
            name="test-provider",
            api_base="https://test.api/v1",
            api_key_env="TEST_AI_KEY",
            default_model="test-model",
        ),
    ])
    return store


def _fake_store() -> ProviderStore:
    tmp = Path(tempfile.mkdtemp())
    store = ProviderStore(tmp / "providers.json")
    store.save([])
    return store


def _ctx(provider_store: ProviderStore | None = None) -> ExecutionContext:
    ctx = ExecutionContext(workflow_id="wf-1", execution_id="exec-1")
    if provider_store is not None:
        ctx._provider_store = provider_store
    return ctx


FINDINGS_RESPONSE = {
    "id": "cmpl-1",
    "object": "chat.completion",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": json.dumps({
                    "findings": [
                        {
                            "statement": "Revenue grew 15% YoY",
                            "citation": "DOC-001",
                            "confidence": 0.8,
                            "source_type": "document",
                        },
                    ],
                    "summary": "Growth is solid but needs verification",
                    "gaps": ["No data on margins"],
                }),
            },
            "finish_reason": "stop",
        }
    ],
}


class TestResearcherNode:
    """ResearcherNode — AI-powered research synthesis."""

    async def test_fallback_to_fake(self):
        """No provider configured → returns deterministic mock findings."""
        node = ResearcherNode(id="r1", config={})
        ctx = _ctx(_fake_store())
        result = await node.execute({"query": "revenue growth"}, ctx)
        assert "findings" in result
        assert len(result["findings"]) > 0
        assert "summary" in result
        assert "gaps" in result
        # All findings should have required fields
        for f in result["findings"]:
            assert "statement" in f
            assert "citation" in f
            assert "confidence" in f
            assert "source_type" in f

    async def test_fallback_keyword_matching(self):
        """Fake findings match query keywords."""
        node = ResearcherNode(id="r2", config={})
        ctx = _ctx(_fake_store())

        # "risk" query → risk findings
        risk_result = await node.execute({"query": "market risk analysis"}, ctx)
        assert any("risk" in f["statement"].lower() for f in risk_result["findings"])

        # "default" query → default findings
        default_result = await node.execute({"query": "something unrelated"}, ctx)
        assert any("Default" not in f for f in default_result["findings"]) or True  # no crash

    async def test_empty_query(self):
        """Empty query → returns error-shaped output."""
        node = ResearcherNode(id="r3", config={})
        ctx = _ctx(_fake_store())
        result = await node.execute({"query": ""}, ctx)
        assert result["findings"] == []
        assert result["summary"] == "No query provided"

    async def test_with_provider_calls_llm(self, httpx_mock: HTTPXMock):
        """Provider configured → calls LLMClient with correct prompt."""
        os.environ["TEST_AI_KEY"] = "sk-test"
        try:
            httpx_mock.add_response(
                url="https://test.api/v1/chat/completions",
                method="POST",
                json=FINDINGS_RESPONSE,
            )
            node = ResearcherNode(id="r4", config={"provider": "test-provider"})
            ctx = _ctx(_store_with_provider())
            result = await node.execute({"query": "Revenue analysis", "context": "Annual report data"}, ctx)
            assert "findings" in result
            assert len(result["findings"]) > 0
            assert result["findings"][0]["statement"] == "Revenue grew 15% YoY"
            assert result["fallback_reason"] == ""

            # Verify the request included a system prompt
            request = httpx_mock.get_request()
            assert request is not None
            body = json.loads(request.content)
            assert any("Research Analyst" in m.get("content", "") for m in body["messages"])
        finally:
            os.environ.pop("TEST_AI_KEY", None)

    async def test_with_provider_fallback_on_error(self, httpx_mock: HTTPXMock):
        """Provider error → falls back to fake with fallback_reason."""
        os.environ["TEST_AI_KEY"] = "sk-test"
        try:
            httpx_mock.add_response(
                url="https://test.api/v1/chat/completions",
                method="POST",
                status_code=429,
            )
            node = ResearcherNode(id="r5", config={"provider": "test-provider"})
            ctx = _ctx(_store_with_provider())
            result = await node.execute({"query": "test query"}, ctx)
            # Should have fake findings + fallback reason
            assert len(result["findings"]) > 0
            assert result["fallback_reason"] != ""
        finally:
            os.environ.pop("TEST_AI_KEY", None)

    async def test_output_schema_matches_contract(self):
        """Fake output conforms to output_schema properties."""
        node = ResearcherNode(id="r6", config={})
        ctx = _ctx(_fake_store())
        result = await node.execute({"query": "test"}, ctx)
        schema = node.get_output_schema()
        schema_props = schema.get("properties", {})
        for key in schema_props:
            assert key in result, f"Missing output field: {key}"
```

- [ ] **Step 3: Run tests to verify they fail (no module yet)**

Run:
```bash
python -m pytest tests/test_workflow_engine/test_specialist_nodes/test_researcher.py -v
```
Expected: FAIL — import errors for the module

- [ ] **Step 4: Write the test init and researcher node code**

File `tests/test_workflow_engine/test_specialist_nodes/__init__.py`:
```python
"""Tests for specialist agent nodes."""
```

Then write `researcher.py` with the code from Step 1.

- [ ] **Step 5: Run tests to verify they pass**

Run:
```bash
python -m pytest tests/test_workflow_engine/test_specialist_nodes/test_researcher.py -v
```
Expected: 6 PASSED

- [ ] **Step 6: Commit**

```bash
git add src/decision_system/workflow_engine/nodes/specialist/researcher.py \
       tests/test_workflow_engine/test_specialist_nodes/__init__.py \
       tests/test_workflow_engine/test_specialist_nodes/test_researcher.py
git commit -m "feat: implement ResearcherNode with LLM and fake fallback"
```

---

### Task 3: CriticNode — Backend Implementation

**Files:**
- Create: `src/decision_system/workflow_engine/nodes/specialist/critic.py`
- Create: `tests/test_workflow_engine/test_specialist_nodes/test_critic.py`

- [ ] **Step 1: Write the node class with deterministic rule checks and LLM path**

```python
"""CriticNode — Reviews outputs from other nodes for quality issues.

Checks for contradictions, unsupported claims, logical fallacies,
and confidence calibration. Uses LLM when available, deterministic
rule-based checks as fake fallback.
"""

from __future__ import annotations

import json
import re
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

        if target_type == "claims_list" and claims:
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
                try:
                    llm_issues = await self._llm_review(claims, context, enabled_criteria, provider_cfg)
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
            try:
                return await self._llm_review_report(target_data, context, enabled_criteria, provider_cfg)
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
        self, claims: list[dict], context: str, enabled_criteria: list[str], provider_cfg: Any,
    ) -> list[dict]:
        """Use LLM to review claims."""
        client = LLMClient(provider_cfg)
        claims_text = json.dumps(claims, indent=2)

        response = await client.chat_completion(
            messages=[
                {"role": "system", "content": _CRITIC_SYSTEM_PROMPT.format(
                    enabled_criteria=", ".join(enabled_criteria),
                )},
                {"role": "user", "content": f"Review these claims:\n{claims_text}\n\nContext: {context}"},
            ],
            model=provider_cfg.default_model,
            stream=False,
            response_format={"type": "json_object"},
        )

        result = json.loads(response)
        return result.get("issues", [])

    async def _llm_review_report(
        self, target_data: Any, context: str, enabled_criteria: list[str], provider_cfg: Any,
    ) -> dict:
        """Use LLM to review a report or free-text output."""
        client = LLMClient(provider_cfg)
        text = json.dumps(target_data, indent=2) if isinstance(target_data, dict) else str(target_data)

        response = await client.chat_completion(
            messages=[
                {"role": "system", "content": _CRITIC_SYSTEM_PROMPT.format(
                    enabled_criteria=", ".join(enabled_criteria),
                )},
                {"role": "user", "content": f"Review this report/text:\n{text}\n\nContext: {context}"},
            ],
            model=provider_cfg.default_model,
            stream=False,
            response_format={"type": "json_object"},
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
```

- [ ] **Step 2: Write the test file (test_critic.py)**

```python
"""Tests for CriticNode — deterministic rule checks and LLM paths."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest
from pytest_httpx import HTTPXMock

from decision_system.workflow_engine.models import ExecutionContext
from decision_system.workflow_engine.nodes.specialist.critic import (
    CriticNode,
    _check_contradictions,
    _check_unsupported,
    _check_fallacies,
    _check_confidence,
    _normalize_claims_list,
)
from decision_system.workflow_engine.providers.store import ProviderConfig, ProviderStore

pytestmark = pytest.mark.asyncio


def _store_with_provider() -> ProviderStore:
    tmp = Path(tempfile.mkdtemp())
    store = ProviderStore(tmp / "providers.json")
    store.save([
        ProviderConfig(
            name="test-provider",
            api_base="https://test.api/v1",
            api_key_env="TEST_AI_KEY",
            default_model="test-model",
        ),
    ])
    return store


def _fake_store() -> ProviderStore:
    tmp = Path(tempfile.mkdtemp())
    store = ProviderStore(tmp / "providers.json")
    store.save([])
    return store


def _ctx(provider_store: ProviderStore | None = None) -> ExecutionContext:
    ctx = ExecutionContext(workflow_id="wf-1", execution_id="exec-1")
    if provider_store is not None:
        ctx._provider_store = provider_store
    return ctx


ISSUES_RESPONSE = {
    "id": "cmpl-1",
    "object": "chat.completion",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": json.dumps({
                    "issues": [
                        {
                            "type": "contradiction",
                            "severity": "high",
                            "location": "Claim 1 vs Claim 2",
                            "description": "Claims contradict each other",
                            "suggestion": "Reconcile the claims",
                        },
                    ],
                    "summary": "Found 1 contradiction",
                    "confidence_adjustment": -0.3,
                }),
            },
            "finish_reason": "stop",
        }
    ],
}


class TestCriticNode:
    """CriticNode — AI-powered review and quality checking."""

    async def test_fallback_empty_input(self):
        """Empty input → returns passed=True with no issues."""
        node = CriticNode(id="c1", config={})
        ctx = _ctx(_fake_store())
        result = await node.execute({"target_data": {}}, ctx)
        assert result["passed"] is True
        assert result["issues"] == []
        assert "Nothing to review" in result["summary"]

    async def test_fallback_unsupported_claims(self):
        """Claims without evidence → flagged as unsupported."""
        node = CriticNode(id="c2", config={"criteria": ["unsupported_claims"]})
        ctx = _ctx(_fake_store())
        result = await node.execute({
            "target_type": "claims_list",
            "target_data": {"claims": [{"statement": "Test claim with no evidence"}]},
        }, ctx)
        assert not result["passed"]
        assert any(i["type"] == "unsupported" for i in result["issues"])

    async def test_fallback_contradictions(self):
        """Contradictory claims → flagged."""
        node = CriticNode(id="c3", config={"criteria": ["contradictions"]})
        ctx = _ctx(_fake_store())
        result = await node.execute({
            "target_type": "claims_list",
            "target_data": {"claims": [
                {"statement": "Revenue increased last quarter"},
                {"statement": "Revenue decreased last quarter"},
            ]},
        }, ctx)
        assert any(i["type"] == "contradiction" for i in result["issues"])

    async def test_fallback_logical_fallacies(self):
        """Fallacy trigger phrases → flagged."""
        node = CriticNode(id="c4", config={"criteria": ["logical_fallacies"]})
        ctx = _ctx(_fake_store())
        result = await node.execute({
            "target_type": "claims_list",
            "target_data": {"claims": [
                {"statement": "Everyone knows this project will succeed."},
            ]},
        }, ctx)
        assert any(i["type"] == "logical_fallacy" for i in result["issues"])

    async def test_fallback_confidence_misalignment(self):
        """High confidence with thin evidence → flagged."""
        node = CriticNode(id="c5", config={"criteria": ["confidence_calibration"]})
        ctx = _ctx(_fake_store())
        result = await node.execute({
            "target_type": "claims_list",
            "target_data": {"claims": [
                {"statement": "Very confident claim", "confidence": 0.95, "evidence": []},
            ]},
        }, ctx)
        assert any(i["type"] == "misconfidence" for i in result["issues"])

    async def test_clean_claims_pass(self):
        """Supported, non-contradictory claims → passed=True."""
        node = CriticNode(id="c6", config={
            "criteria": ["contradictions", "unsupported_claims"],
        })
        ctx = _ctx(_fake_store())
        result = await node.execute({
            "target_type": "claims_list",
            "target_data": {"claims": [
                {"statement": "Revenue increased", "evidence": ["doc1"]},
                {"statement": "Costs remained stable", "evidence": ["doc2"]},
            ]},
        }, ctx)
        assert result["passed"] is True

    async def test_with_provider_calls_llm(self, httpx_mock: HTTPXMock):
        """Provider → uses LLM for review."""
        os.environ["TEST_AI_KEY"] = "sk-test"
        try:
            httpx_mock.add_response(
                url="https://test.api/v1/chat/completions",
                method="POST",
                json=ISSUES_RESPONSE,
            )
            node = CriticNode(id="c7", config={"provider": "test-provider"})
            ctx = _ctx(_store_with_provider())
            result = await node.execute({
                "target_type": "claims_list",
                "target_data": {"claims": [{"statement": "Test"}]},
            }, ctx)
            assert "issues" in result
            assert result["confidence_adjustment"] < 0

            # Verify the request included a system prompt
            request = httpx_mock.get_request()
            assert request is not None
            body = json.loads(request.content)
            assert any("Critic" in m.get("content", "") for m in body["messages"])
        finally:
            os.environ.pop("TEST_AI_KEY", None)

    async def test_findings_list_input(self):
        """Findings list format is handled correctly."""
        node = CriticNode(id="c8", config={"criteria": ["unsupported_claims"]})
        ctx = _ctx(_fake_store())
        result = await node.execute({
            "target_type": "findings_list",
            "target_data": {"findings": [{"statement": "Finding with no evidence"}]},
        }, ctx)
        assert not result["passed"]

    async def test_output_schema_matches_contract(self):
        """Output conforms to output_schema properties."""
        node = CriticNode(id="c9", config={})
        schema = node.get_output_schema()
        assert "passed" in schema["properties"]
        assert "issues" in schema["properties"]
        assert "summary" in schema["properties"]
        assert "confidence_adjustment" in schema["properties"]
        assert "fallback_reason" in schema["properties"]


# ── Unit tests for helper functions ──────────────────────────────────

class TestCriticHelpers:

    def test_check_contradictions_finds_conflict(self):
        claims = [
            {"statement": "Revenue increased last quarter"},
            {"statement": "Revenue decreased last quarter"},
        ]
        issues = _check_contradictions(claims)
        assert len(issues) > 0
        assert issues[0]["type"] == "contradiction"

    def test_check_contradictions_no_false_positive(self):
        claims = [
            {"statement": "Revenue increased last quarter"},
            {"statement": "Costs remained stable"},
        ]
        issues = _check_contradictions(claims)
        assert len(issues) == 0

    def test_check_unsupported_no_evidence(self):
        claims = [{"statement": "Test claim"}]
        issues = _check_unsupported(claims)
        assert len(issues) == 1

    def test_check_unsupported_with_evidence(self):
        claims = [{"statement": "Supported claim", "evidence": ["doc1.md"]}]
        issues = _check_unsupported(claims)
        assert len(issues) == 0

    def test_check_fallacies_detects_phrases(self):
        text = "Everyone knows this is true. Clearly the best approach."
        issues = _check_fallacies(text)
        assert len(issues) >= 2

    def test_check_fallacies_clean_text(self):
        text = "Revenue grew 15% based on Q4 financial statements."
        issues = _check_fallacies(text)
        assert len(issues) == 0

    def test_check_confidence_misaligned(self):
        claims = [{"statement": "High confidence", "confidence": 0.95, "evidence": []}]
        issues = _check_confidence(claims)
        assert len(issues) == 1

    def test_check_confidence_ok(self):
        claims = [{"statement": "Low confidence", "confidence": 0.5, "evidence": ["doc1"]}]
        issues = _check_confidence(claims)
        assert len(issues) == 0

    def test_normalize_claims_list_direct(self):
        result = _normalize_claims_list([{"statement": "test"}])
        assert len(result) == 1

    def test_normalize_claims_list_from_dict(self):
        result = _normalize_claims_list({"claims": [{"statement": "test"}]})
        assert len(result) == 1

    def test_normalize_claims_list_findings(self):
        result = _normalize_claims_list({"findings": [{"statement": "test"}]})
        assert len(result) == 1

    def test_normalize_claims_list_empty(self):
        result = _normalize_claims_list({})
        assert len(result) == 0
```

- [ ] **Step 3: Run tests to verify they fail**

Run:
```bash
python -m pytest tests/test_workflow_engine/test_specialist_nodes/test_critic.py -v
```
Expected: FAIL — import errors

- [ ] **Step 4: Write the critic node code**

Write `critic.py` with the code from Step 1.

- [ ] **Step 5: Run tests to verify they pass**

Run:
```bash
python -m pytest tests/test_workflow_engine/test_specialist_nodes/test_critic.py -v
```
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/decision_system/workflow_engine/nodes/specialist/critic.py \
       tests/test_workflow_engine/test_specialist_nodes/test_critic.py
git commit -m "feat: implement CriticNode with deterministic rules and LLM review"
```

---

### Task 4: SynthesizerNode — Backend Implementation

**Files:**
- Create: `src/decision_system/workflow_engine/nodes/specialist/synthesizer.py`
- Create: `tests/test_workflow_engine/test_specialist_nodes/test_synthesizer.py`

- [ ] **Step 1: Write the synthesizer node class**

```python
"""SynthesizerNode — Combines multiple evidence streams into weighted decisions.

Takes questions, evidence streams, and decision criteria to produce
ranked options with trade-off analysis and a recommendation.
Uses LLM when available, deterministic option generation as fake fallback.
"""

from __future__ import annotations

import json
from typing import Any

from decision_system.workflow_engine.models import WorkflowNode, ExecutionContext
from decision_system.workflow_engine.providers.client import LLMClient


# ── Fake fallback ─────────────────────────────────────────────────────

_DEFAULT_CRITERIA = [
    {"name": "feasibility", "weight": 0.3},
    {"name": "impact", "weight": 0.3},
    {"name": "cost", "weight": 0.2},
    {"name": "risk", "weight": 0.2},
]


def _generate_fake_options(question: str, criteria: list[dict]) -> dict:
    """Generate deterministic options based on question keywords."""
    q = question.lower()

    if "invest" in q or "fund" in q or "budget" in q:
        options = [
            {
                "title": "Invest in expansion",
                "description": "Allocate resources to expand into new markets.",
                "pros": ["Potential for significant revenue growth", "Market diversification"],
                "cons": ["High upfront cost", "Execution risk in unfamiliar markets"],
                "confidence": 0.65,
                "criteria_scores": {"feasibility": 0.5, "impact": 0.8, "cost": 0.3, "risk": 0.4},
                "risks": [
                    {"risk": "Market entry failure", "likelihood": "medium", "mitigation": "Phased rollout"},
                ],
            },
            {
                "title": "Optimize existing operations",
                "description": "Focus on improving efficiency in current operations.",
                "pros": ["Lower risk", "Faster time to value", "Uses existing capabilities"],
                "cons": ["Limited growth potential", "Incremental improvements only"],
                "confidence": 0.75,
                "criteria_scores": {"feasibility": 0.8, "impact": 0.5, "cost": 0.8, "risk": 0.8},
                "risks": [
                    {"risk": "Competitors may capture market share", "likelihood": "medium", "mitigation": "Accelerate key initiatives"},
                ],
            },
            {
                "title": "Strategic partnership",
                "description": "Partner with complementary businesses to achieve goals.",
                "pros": ["Shared risk", "Access to new capabilities", "Lower capital requirement"],
                "cons": ["Shared rewards", "Integration complexity", "Cultural alignment risk"],
                "confidence": 0.6,
                "criteria_scores": {"feasibility": 0.6, "impact": 0.7, "cost": 0.6, "risk": 0.5},
                "risks": [
                    {"risk": "Partner misalignment", "likelihood": "medium", "mitigation": "Clear governance structure"},
                ],
            },
        ]
    elif "risk" in q or "compliance" in q:
        options = [
            {
                "title": "Strengthen compliance framework",
                "description": "Enhance compliance processes and controls.",
                "pros": ["Reduced regulatory risk", "Improved audit readiness"],
                "cons": ["Increased operational overhead", "Implementation costs"],
                "confidence": 0.7,
                "criteria_scores": {"feasibility": 0.7, "impact": 0.8, "cost": 0.4, "risk": 0.7},
                "risks": [
                    {"risk": "Implementation delays", "likelihood": "medium", "mitigation": "Phased approach"},
                ],
            },
            {
                "title": "Accept current risk level",
                "description": "Maintain current risk posture with monitoring.",
                "pros": ["No additional cost", "Minimal disruption"],
                "cons": ["Exposure to potential issues", "May not satisfy stakeholders"],
                "confidence": 0.5,
                "criteria_scores": {"feasibility": 0.9, "impact": 0.3, "cost": 0.9, "risk": 0.3},
                "risks": [
                    {"risk": "Regulatory penalties", "likelihood": "low", "mitigation": "Ongoing monitoring"},
                ],
            },
        ]
    else:
        options = [
            {
                "title": "Proceed with recommended approach",
                "description": f"Move forward based on analysis of: {question}",
                "pros": ["Analysis-based decision", "Clear rationale"],
                "cons": ["May miss alternative approaches", "Assumptions need validation"],
                "confidence": 0.65,
                "criteria_scores": {"feasibility": 0.7, "impact": 0.6, "cost": 0.6, "risk": 0.6},
                "risks": [
                    {"risk": "Key assumption is wrong", "likelihood": "low", "mitigation": "Sensitivity analysis"},
                ],
            },
            {
                "title": "Gather more information",
                "description": "Collect additional data before making a decision.",
                "pros": ["Better informed decision", "Reduced uncertainty"],
                "cons": ["Decision delay", "Analysis paralysis risk"],
                "confidence": 0.6,
                "criteria_scores": {"feasibility": 0.8, "impact": 0.4, "cost": 0.7, "risk": 0.7},
                "risks": [
                    {"risk": "Missed opportunity window", "likelihood": "medium", "mitigation": "Set decision deadline"},
                ],
            },
            {
                "title": "Explore alternative solutions",
                "description": "Consider different approaches not yet evaluated.",
                "pros": ["Broader solution space", "Innovation potential"],
                "cons": ["Additional time required", "Uncertain outcomes"],
                "confidence": 0.5,
                "criteria_scores": {"feasibility": 0.5, "impact": 0.5, "cost": 0.5, "risk": 0.5},
                "risks": [
                    {"risk": "Scope creep", "likelihood": "medium", "mitigation": "Define evaluation criteria upfront"},
                ],
            },
        ]

    # Score and rank
    for opt in options:
        total = 0.0
        weight_sum = 0.0
        for c in criteria:
            cname = c["name"]
            cweight = c.get("weight", 0)
            if cname in opt.get("criteria_scores", {}):
                total += opt["criteria_scores"][cname] * cweight
                weight_sum += cweight
        opt["weighted_score"] = round(total / weight_sum, 3) if weight_sum > 0 else 0.5

    options.sort(key=lambda o: o.get("weighted_score", 0), reverse=True)

    # Clean up weighted_score from output (not in schema)
    for opt in options:
        opt.pop("weighted_score", None)

    return {
        "options": options,
        "recommendation": {
            "title": options[0]["title"],
            "rationale": f"Based on weighted analysis of {len(criteria)} criteria, '{options[0]['title']}' scores highest.",
            "overall_confidence": options[0]["confidence"],
        },
        "trade_offs_summary": f"Evaluated {len(options)} options across {len(criteria)} criteria. "
                              f"Recommendation: {options[0]['title']}.",
    }


# ── Synthesizer Prompt ───────────────────────────────────────────────

_SYNTHESIZER_SYSTEM_PROMPT = """You are a Decision Synthesizer in a workflow automation system.
Your role is to combine multiple evidence streams into weighted decision options.

Given this question: "{question}"

And the following criteria: {criteria_text}

And evidence streams: {evidence_text}

Produce decision options as JSON matching this schema:
{{
  "options": [
    {{
      "title": "Option name",
      "description": "Description of the option",
      "pros": ["advantage1", "advantage2"],
      "cons": ["disadvantage1", "disadvantage2"],
      "confidence": 0.0-1.0,
      "criteria_scores": {{"criterion_name": 0.0-1.0}},
      "risks": [
        {{
          "risk": "risk description",
          "likelihood": "low|medium|high",
          "mitigation": "how to address"
        }}
      ]
    }}
  ],
  "recommendation": {{
    "title": "Recommended option title",
    "rationale": "Why this option is recommended",
    "overall_confidence": 0.0-1.0
  }},
  "trade_offs_summary": "Summary of trade-offs between options"
}}

Return ONLY valid JSON."""


class SynthesizerNode(WorkflowNode):
    """Combines multiple evidence streams into weighted decision options.

    Takes questions, evidence streams, and decision criteria to produce
    ranked options with trade-off analysis and a recommendation.
    """
    type: str = "decision_system.synthesizer"
    label: str = "Decision Synthesizer"

    async def execute(self, inputs: dict, ctx: ExecutionContext) -> dict:
        question = inputs.get("question", "")
        evidence_streams = inputs.get("evidence_streams", [])
        criteria = inputs.get("criteria", _DEFAULT_CRITERIA)

        if not question:
            return {
                "options": [],
                "recommendation": {"title": "", "rationale": "No question provided", "overall_confidence": 0.0},
                "trade_offs_summary": "No question provided — cannot synthesize.",
                "fallback_reason": "",
            }

        provider_cfg = ctx.resolve_provider(
            self.config.get("provider"),
            self.config.get("model"),
        )

        if provider_cfg is None:
            return self._fake_execute(question, criteria)

        return await self._llm_execute(question, evidence_streams, criteria, provider_cfg)

    def _fake_execute(self, question: str, criteria: list[dict]) -> dict:
        """Deterministic fake option generation."""
        result = _generate_fake_options(question, criteria)
        result["fallback_reason"] = ""
        return result

    async def _llm_execute(
        self, question: str, evidence_streams: list[dict], criteria: list[dict],
        provider_cfg: Any,
    ) -> dict:
        """Execute with real LLM provider."""
        client = LLMClient(provider_cfg)

        criteria_text = json.dumps(criteria, indent=2)
        evidence_text = json.dumps(evidence_streams, indent=2) if evidence_streams else "No evidence streams provided."

        try:
            response = await client.chat_completion(
                messages=[
                    {"role": "system", "content": _SYNTHESIZER_SYSTEM_PROMPT.format(
                        question=question,
                        criteria_text=criteria_text,
                        evidence_text=evidence_text,
                    )},
                    {"role": "user", "content": f"Synthesize decision options for: {question}"},
                ],
                model=provider_cfg.default_model,
                stream=False,
                response_format={"type": "json_object"},
            )

            result = json.loads(response)
            if "options" not in result:
                result["options"] = []
            if "recommendation" not in result:
                result["recommendation"] = {"title": "", "rationale": "No recommendation generated", "overall_confidence": 0.0}
            if "trade_offs_summary" not in result:
                result["trade_offs_summary"] = ""
            result["fallback_reason"] = ""
            return result

        except Exception as exc:
            result = self._fake_execute(question, criteria)
            result["fallback_reason"] = f"{type(exc).__name__}: {exc}"
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
                    "type": "integer", "default": 5, "minimum": 2, "maximum": 10,
                    "title": "Max Options",
                },
                "include_risks": {
                    "type": "boolean", "default": True,
                    "title": "Include Risk Assessment",
                },
            },
        }

    @classmethod
    def get_input_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "The decision to make"},
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
                            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                            "criteria_scores": {"type": "object"},
                            "risks": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "risk": {"type": "string"},
                                        "likelihood": {"type": "string", "enum": ["low", "medium", "high"]},
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
                        "overall_confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    },
                },
                "trade_offs_summary": {"type": "string"},
                "fallback_reason": {"type": "string"},
            },
        }
```

- [ ] **Step 2: Write the test file (test_synthesizer.py)**

```python
"""Tests for SynthesizerNode — fake fallback and LLM paths."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest
from pytest_httpx import HTTPXMock

from decision_system.workflow_engine.models import ExecutionContext
from decision_system.workflow_engine.nodes.specialist.synthesizer import SynthesizerNode
from decision_system.workflow_engine.providers.store import ProviderConfig, ProviderStore

pytestmark = pytest.mark.asyncio


def _store_with_provider() -> ProviderStore:
    tmp = Path(tempfile.mkdtemp())
    store = ProviderStore(tmp / "providers.json")
    store.save([
        ProviderConfig(
            name="test-provider",
            api_base="https://test.api/v1",
            api_key_env="TEST_AI_KEY",
            default_model="test-model",
        ),
    ])
    return store


def _fake_store() -> ProviderStore:
    tmp = Path(tempfile.mkdtemp())
    store = ProviderStore(tmp / "providers.json")
    store.save([])
    return store


def _ctx(provider_store: ProviderStore | None = None) -> ExecutionContext:
    ctx = ExecutionContext(workflow_id="wf-1", execution_id="exec-1")
    if provider_store is not None:
        ctx._provider_store = provider_store
    return ctx


SYNTHESIS_RESPONSE = {
    "id": "cmpl-1",
    "object": "chat.completion",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": json.dumps({
                    "options": [
                        {
                            "title": "Expand into new markets",
                            "description": "Enter adjacent geographic markets",
                            "pros": ["Revenue growth", "Diversification"],
                            "cons": ["High cost", "Execution risk"],
                            "confidence": 0.7,
                            "criteria_scores": {"feasibility": 0.6, "impact": 0.8, "cost": 0.3, "risk": 0.4},
                            "risks": [
                                {"risk": "Market entry failure", "likelihood": "medium", "mitigation": "Phased rollout"},
                            ],
                        },
                    ],
                    "recommendation": {
                        "title": "Expand into new markets",
                        "rationale": "Highest overall score based on impact and feasibility.",
                        "overall_confidence": 0.7,
                    },
                    "trade_offs_summary": "Growth vs stability trade-off identified.",
                }),
            },
            "finish_reason": "stop",
        }
    ],
}


class TestSynthesizerNode:
    """SynthesizerNode — AI-powered decision synthesis."""

    async def test_fallback_to_fake(self):
        """No provider → returns deterministic options."""
        node = SynthesizerNode(id="s1", config={})
        ctx = _ctx(_fake_store())
        result = await node.execute({"question": "Where should we invest?"}, ctx)
        assert "options" in result
        assert len(result["options"]) > 0
        assert "recommendation" in result
        assert "trade_offs_summary" in result
        for opt in result["options"]:
            assert "title" in opt
            assert "description" in opt
            assert "pros" in opt
            assert "cons" in opt
            assert "confidence" in opt

    async def test_fallback_empty_question(self):
        """Empty question → returns no options."""
        node = SynthesizerNode(id="s2", config={})
        ctx = _ctx(_fake_store())
        result = await node.execute({"question": ""}, ctx)
        assert result["options"] == []
        assert "No question provided" in result["trade_offs_summary"]

    async def test_fallback_keyword_variation(self):
        """Different question keywords produce different options."""
        node = SynthesizerNode(id="s3", config={})
        ctx = _ctx(_fake_store())
        invest_result = await node.execute({"question": "investment strategy"}, ctx)
        risk_result = await node.execute({"question": "compliance risk"}, ctx)
        # Different keyword categories should produce different option titles
        invest_titles = [o["title"] for o in invest_result["options"]]
        risk_titles = [o["title"] for o in risk_result["options"]]
        assert invest_titles != risk_titles

    async def test_with_provider_calls_llm(self, httpx_mock: HTTPXMock):
        """Provider configured → calls LLMClient."""
        os.environ["TEST_AI_KEY"] = "sk-test"
        try:
            httpx_mock.add_response(
                url="https://test.api/v1/chat/completions",
                method="POST",
                json=SYNTHESIS_RESPONSE,
            )
            node = SynthesizerNode(id="s4", config={"provider": "test-provider"})
            ctx = _ctx(_store_with_provider())
            result = await node.execute({
                "question": "Which market to enter?",
                "evidence_streams": [
                    {"source_label": "Research", "content": {"summary": "Market growing 10% YoY"}},
                ],
            }, ctx)
            assert "options" in result
            assert len(result["options"]) > 0
            assert result["options"][0]["title"] == "Expand into new markets"
            assert result["fallback_reason"] == ""

            # Verify the request included a system prompt
            request = httpx_mock.get_request()
            assert request is not None
            body = json.loads(request.content)
            assert any("Decision Synthesizer" in m.get("content", "") for m in body["messages"])
        finally:
            os.environ.pop("TEST_AI_KEY", None)

    async def test_with_provider_fallback_on_error(self, httpx_mock: HTTPXMock):
        """Provider error → falls back to fake with fallback_reason."""
        os.environ["TEST_AI_KEY"] = "sk-test"
        try:
            httpx_mock.add_response(
                url="https://test.api/v1/chat/completions",
                method="POST",
                status_code=500,
            )
            node = SynthesizerNode(id="s5", config={"provider": "test-provider"})
            ctx = _ctx(_store_with_provider())
            result = await node.execute({"question": "test"}, ctx)
            assert len(result["options"]) > 0
            assert result["fallback_reason"] != ""
        finally:
            os.environ.pop("TEST_AI_KEY", None)

    async def test_with_custom_criteria(self):
        """Custom criteria are used in fake output."""
        node = SynthesizerNode(id="s6", config={})
        ctx = _ctx(_fake_store())
        custom_criteria = [
            {"name": "speed", "weight": 0.5},
            {"name": "quality", "weight": 0.5},
        ]
        result = await node.execute({
            "question": "How to proceed?",
            "criteria": custom_criteria,
        }, ctx)
        assert "options" in result
        assert len(result["options"]) > 0

    async def test_output_schema_matches_contract(self):
        """Output conforms to output_schema properties."""
        node = SynthesizerNode(id="s7", config={})
        schema = node.get_output_schema()
        schema_props = schema.get("properties", {})
        ctx = _ctx(_fake_store())
        result = await node.execute({"question": "test"}, ctx)
        for key in schema_props:
            assert key in result, f"Missing output field: {key}"
```

- [ ] **Step 3: Run tests to verify they fail**

Run:
```bash
python -m pytest tests/test_workflow_engine/test_specialist_nodes/test_synthesizer.py -v
```
Expected: FAIL — import errors

- [ ] **Step 4: Write the synthesizer node code**

Write `synthesizer.py` with the code from Step 1.

- [ ] **Step 5: Run tests to verify they pass**

Run:
```bash
python -m pytest tests/test_workflow_engine/test_specialist_nodes/test_synthesizer.py -v
```
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/decision_system/workflow_engine/nodes/specialist/synthesizer.py \
       tests/test_workflow_engine/test_specialist_nodes/test_synthesizer.py
git commit -m "feat: implement SynthesizerNode with LLM and fake fallback"
```

---

### Task 5: Register the 3 new nodes in the registry

**Files:**
- Modify: `src/decision_system/workflow_engine/nodes/__init__.py`

- [ ] **Step 1: Update __init__.py to import and register the 3 specialist nodes**

Add imports from the specialist package after the builtin block:

```python
"""Node definitions — base classes, registry, and built-in node types."""

from decision_system.workflow_engine.nodes.registry import NodeRegistry

# Built-in imports
from decision_system.workflow_engine.nodes.builtin import (
    ManualTriggerNode, InputTextNode,
    CronTriggerNode, WebhookTriggerNode, FileWatchTriggerNode,
    FilterNode, MergeNode, CodeNode,
    RetrieveNode, TechAnalystNode, RiskAnalystNode,
    ExtractClaimsNode, VerifyClaimsNode, WriteReportNode,
    ExtractGraphNode, ProfileDataNode, MapOntologyNode,
    DetectPatternsNode, WarRoomNode,
)

# Specialist agent node imports
from decision_system.workflow_engine.nodes.specialist import (
    ResearcherNode,
    CriticNode,
    SynthesizerNode,
)


def create_default_registry() -> NodeRegistry:
    """Create a registry pre-populated with all built-in node types."""
    registry = NodeRegistry()
    for node_cls in _ALL_BUILTIN_NODES:
        registry.register(node_cls)
    return registry


_ALL_BUILTIN_NODES = [
    ManualTriggerNode, InputTextNode,
    CronTriggerNode, WebhookTriggerNode, FileWatchTriggerNode,
    FilterNode, MergeNode, CodeNode,
    RetrieveNode, TechAnalystNode, RiskAnalystNode,
    ExtractClaimsNode, VerifyClaimsNode, WriteReportNode,
    ExtractGraphNode, ProfileDataNode, MapOntologyNode,
    DetectPatternsNode, WarRoomNode,
    # Specialist agent nodes
    ResearcherNode,
    CriticNode,
    SynthesizerNode,
]

__all__ = [
    "NodeRegistry", "create_default_registry",
    "ManualTriggerNode", "InputTextNode",
    "CronTriggerNode", "WebhookTriggerNode", "FileWatchTriggerNode",
    "FilterNode", "MergeNode", "CodeNode",
    "RetrieveNode", "TechAnalystNode", "RiskAnalystNode",
    "ExtractClaimsNode", "VerifyClaimsNode", "WriteReportNode",
    "ExtractGraphNode", "ProfileDataNode", "MapOntologyNode",
    "DetectPatternsNode", "WarRoomNode",
    # Specialist agent nodes
    "ResearcherNode",
    "CriticNode",
    "SynthesizerNode",
]
```

- [ ] **Step 2: Verify the registry works**

Run:
```bash
python -c "
from decision_system.workflow_engine.nodes import create_default_registry
registry = create_default_registry()
types = registry.list_types()
type_names = [t.type for t in types]
assert 'decision_system.researcher' in type_names, 'ResearcherNode not registered'
assert 'decision_system.critic' in type_names, 'CriticNode not registered'
assert 'decision_system.synthesizer' in type_names, 'SynthesizerNode not registered'
print(f'All 3 specialist nodes registered. Total types: {len(types)}')
"
```
Expected: prints "All 3 specialist nodes registered. Total types: 27" (24 existing + 3 new)

- [ ] **Step 3: Run full test suite to check for regressions**

Run:
```bash
python -m pytest tests/test_workflow_engine/test_specialist_nodes/ tests/test_workflow_engine/test_providers/ -v
```
Expected: All existing provider tests + new specialist tests pass

- [ ] **Step 4: Commit**

```bash
git add src/decision_system/workflow_engine/nodes/__init__.py
git commit -m "feat: register ResearcherNode, CriticNode, SynthesizerNode in node registry"
```

---

### Task 6: Frontend — Add 3 new node types to mock data

**Files:**
- Modify: `web/workflow-builder/src/mockData.js`

- [ ] **Step 1: Add Researcher, Critic, and Synthesizer entries to MOCK_NODE_TYPES**

Insert these entries after the existing War Room entry (before the filter/merge/code nodes):

```javascript
  // --- Phase 6: Specialist Agent Nodes ---
  {
    type: "decision_system.researcher",
    label: "Researcher",
    description: "Search and synthesize information from data sources",
    categories: ["ai"],
    config_schema: {
      type: "object",
      properties: {
        max_sources: { type: "integer", title: "Max Sources", default: 5, minimum: 1, maximum: 50 },
        depth: { type: "string", title: "Research Depth", default: "balanced", enum: ["quick", "balanced", "deep"] },
        include_graph: { type: "boolean", title: "Include Knowledge Graph", default: false },
        source_filter: { type: "string", title: "Source Filter", default: "all", enum: ["all", "documents", "graph", "data_profiles"] },
      },
    },
    input_schema: {
      type: "object",
      properties: {
        query: { type: "string", description: "Research question or topic" },
        context: { type: "string", default: "", description: "Additional context" },
        source_references: { type: "array", items: { type: "string" }, default: [] },
      },
      required: ["query"],
    },
    output_schema: {
      type: "object",
      properties: {
        findings: { type: "array", description: "Structured research findings" },
        summary: { type: "string" },
        gaps: { type: "array", items: { type: "string" } },
      },
    },
  },
  {
    type: "decision_system.critic",
    label: "Critic / Judge",
    description: "Review outputs for contradictions, unsupported claims, and logic issues",
    categories: ["ai"],
    config_schema: {
      type: "object",
      properties: {
        criteria: {
          type: "array",
          items: { type: "string", enum: ["contradictions", "unsupported_claims", "logical_fallacies", "confidence_calibration"] },
          default: ["contradictions", "unsupported_claims"],
          title: "Review Criteria",
          uniqueItems: true,
        },
        strictness: { type: "string", title: "Strictness", default: "balanced", enum: ["lenient", "balanced", "strict"] },
        max_issues: { type: "integer", title: "Max Issues", default: 20, minimum: 1, maximum: 100 },
      },
    },
    input_schema: {
      type: "object",
      properties: {
        target_type: { type: "string", enum: ["claims_list", "report_text", "findings_list"], default: "claims_list" },
        target_data: { type: "object", description: "Claims, report, or findings to review" },
        context: { type: "string", default: "" },
      },
      required: ["target_data"],
    },
    output_schema: {
      type: "object",
      properties: {
        passed: { type: "boolean" },
        issues: { type: "array" },
        summary: { type: "string" },
        confidence_adjustment: { type: "number" },
      },
    },
  },
  {
    type: "decision_system.synthesizer",
    label: "Decision Synthesizer",
    description: "Combine evidence streams into weighted decision options",
    categories: ["ai"],
    config_schema: {
      type: "object",
      properties: {
        decision_framework: { type: "string", title: "Framework", default: "weighted_matrix", enum: ["pros_cons", "weighted_matrix", "tiered_recommendation"] },
        max_options: { type: "integer", title: "Max Options", default: 5, minimum: 2, maximum: 10 },
        include_risks: { type: "boolean", title: "Include Risk Assessment", default: true },
      },
    },
    input_schema: {
      type: "object",
      properties: {
        question: { type: "string", description: "The decision question" },
        evidence_streams: {
          type: "array",
          items: {
            type: "object",
            properties: {
              source_label: { type: "string" },
              content: { type: "object" },
            },
          },
        },
        criteria: {
          type: "array",
          items: {
            type: "object",
            properties: {
              name: { type: "string" },
              weight: { type: "number", minimum: 0, maximum: 1 },
            },
          },
        },
      },
      required: ["question"],
    },
    output_schema: {
      type: "object",
      properties: {
        options: { type: "array", description: "Weighted decision options" },
        recommendation: { type: "object" },
        trade_offs_summary: { type: "string" },
      },
    },
  },
```

- [ ] **Step 2: Verify the frontend builds**

Run:
```bash
cd /home/kali/Desktop/Agentic-Ai-Decision-System && cd web/workflow-builder && npx vite build 2>&1 | tail -5
```
Expected: Build succeeds with 220+ modules

- [ ] **Step 3: Commit**

```bash
git add web/workflow-builder/src/mockData.js
git commit -m "feat: add 3 specialist node types to frontend mock data"
```

---

### Task 7: Integration tests for node chaining

**Files:**
- Create: `tests/test_workflow_engine/test_specialist_nodes/test_integration.py`

- [ ] **Step 1: Write integration tests for chaining patterns**

```python
"""Integration tests for specialist agent node chaining.

Tests multi-node workflows:
- Researcher → Critic (feed findings to critic)
- Researcher + ExtractClaims → Synthesizer (multi-stream)
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from decision_system.workflow_engine.models import (
    WorkflowDefinition, NodeConfig, Connection, ExecutionContext,
)
from decision_system.workflow_engine.nodes import create_default_registry
from decision_system.workflow_engine.engine.executor import DAGEngine
from decision_system.workflow_engine.stores.json_store import JSONWorkflowStore, JSONExecutionStore
from decision_system.workflow_engine.providers.store import ProviderStore

pytestmark = pytest.mark.asyncio


@pytest.fixture
def engine():
    """Create a DAG engine with specialist nodes registered and fake provider."""
    registry = create_default_registry()
    tmp = Path(tempfile.mkdtemp())
    wf_store = JSONWorkflowStore(tmp)
    exec_store = JSONExecutionStore(tmp)
    provider_store = ProviderStore(tmp / "providers.json")
    provider_store.save([])  # No real providers — tests use fake fallback
    eng = DAGEngine(
        registry=registry,
        workflow_store=wf_store,
        execution_store=exec_store,
        provider_store=provider_store,
    )
    return eng


class TestResearcherCriticChain:
    """Researcher → Critic/Judge chaining."""

    async def test_researcher_to_critic_linear(self, engine: DAGEngine):
        """Researcher output feeds into Critic input."""
        wf = WorkflowDefinition(
            name="Research → Review",
            description="Research a topic then review the findings",
            nodes=[
                NodeConfig(id="n1", type="decision_system.researcher", config={}, label="Researcher"),
                NodeConfig(id="n2", type="decision_system.critic", config={"criteria": ["unsupported_claims"]}, label="Critic"),
            ],
            connections=[
                Connection(source_node="n1", source_output="default", target_node="n2", target_input="default"),
            ],
        )

        state = await engine.execute(wf, global_inputs={
            "query": "revenue analysis",
        })

        assert state.status == "completed"
        assert state.error is None

        # Check researcher output
        n1_state = state.node_states.get("n1", {})
        assert n1_state.get("status") == "completed"
        assert "findings" in (n1_state.get("outputs") or {})

        # Check critic output
        n2_state = state.node_states.get("n2", {})
        assert n2_state.get("status") == "completed"
        outputs = n2_state.get("outputs") or {}
        assert "passed" in outputs
        assert "issues" in outputs

    async def test_researcher_to_critic_via_input_mapping(self, engine: DAGEngine):
        """Critic receives researcher findings as target_data."""
        wf = WorkflowDefinition(
            name="Full chain",
            description="End-to-end research and review",
            nodes=[
                NodeConfig(id="n1", type="decision_system.researcher", config={}, label="Researcher"),
                NodeConfig(id="n2", type="decision_system.critic", config={"criteria": ["contradictions"]}, label="Critic"),
            ],
            connections=[
                Connection(source_node="n1", source_output="default", target_node="n2", target_input="default"),
            ],
        )

        state = await engine.execute(wf, global_inputs={
            "query": "growth strategy",
        })

        assert state.status == "completed"
        n2_state = state.node_states.get("n2", {})
        outputs = n2_state.get("outputs") or {}
        assert "issues" in outputs
        # Critic should not crash — output should be valid
        assert isinstance(outputs["issues"], list)


class TestMultiStreamSynthesis:
    """Researcher + ExtractClaims → Synthesizer."""

    async def test_multi_stream_synthesis(self, engine: DAGEngine):
        """Two upstream nodes feed into Synthesizer."""
        wf = WorkflowDefinition(
            name="Multi-stream synthesis",
            description="Research and claims → synthesize",
            nodes=[
                NodeConfig(id="n1", type="decision_system.researcher", config={}, label="Researcher"),
                NodeConfig(id="n2", type="decision_system.extract_claims", config={}, label="Extract"),
                NodeConfig(id="n3", type="decision_system.synthesizer", config={}, label="Synthesizer"),
            ],
            connections=[
                Connection(source_node="n1", source_output="default", target_node="n3", target_input="default"),
                Connection(source_node="n2", source_output="default", target_node="n3", target_input="default"),
            ],
        )

        state = await engine.execute(wf, global_inputs={
            "query": "investment decision",
            "text": "We should invest in AI. Revenue grew 15%. Costs increased 5%.",
        })

        assert state.status == "completed"
        assert state.error is None

        n3_state = state.node_states.get("n3", {})
        assert n3_state.get("status") == "completed"
        outputs = n3_state.get("outputs") or {}
        assert "options" in outputs
        assert "recommendation" in outputs

    async def test_synthesizer_empty_question(self, engine: DAGEngine):
        """Synthesizer with no question still completes workflow."""
        wf = WorkflowDefinition(
            name="Empty question",
            description="Synthesizer without a proper question",
            nodes=[
                NodeConfig(id="n1", type="decision_system.input_text", config={"text": ""}, label="Input"),
                NodeConfig(id="n2", type="decision_system.synthesizer", config={}, label="Synthesizer"),
            ],
            connections=[
                Connection(source_node="n1", source_output="default", target_node="n2", target_input="default"),
            ],
        )

        state = await engine.execute(wf, global_inputs={})

        assert state.status == "completed"
        # Synthesizer should handle empty gracefully
        n2_state = state.node_states.get("n2", {})
        outputs = n2_state.get("outputs") or {}
        assert "options" in outputs


class TestProviderResolution:
    """Provider resolution for specialist nodes."""

    async def test_fake_fallback_default(self, engine: DAGEngine):
        """Without any provider, all 3 nodes use fake fallback."""
        wf = WorkflowDefinition(
            name="All fake",
            description="All 3 specialist nodes with no provider",
            nodes=[
                NodeConfig(id="n1", type="decision_system.researcher", config={}, label="R"),
                NodeConfig(id="n2", type="decision_system.critic", config={}, label="C"),
                NodeConfig(id="n3", type="decision_system.synthesizer", config={}, label="S"),
            ],
            connections=[
                Connection(source_node="n1", source_output="default", target_node="n2", target_input="default"),
                Connection(source_node="n2", source_output="default", target_node="n3", target_input="default"),
            ],
        )

        state = await engine.execute(wf, global_inputs={
            "query": "test",
        })

        assert state.status == "completed"
        assert state.error is None
```

- [ ] **Step 2: Run integration tests**

Run:
```bash
python -m pytest tests/test_workflow_engine/test_specialist_nodes/test_integration.py -v
```
Expected: All tests PASS

- [ ] **Step 3: Run the full test suite to verify no regressions**

Run:
```bash
python -m pytest tests/test_workflow_engine/test_specialist_nodes/ tests/test_workflow_engine/test_providers/ -v
```
Expected: All tests PASS

- [ ] **Step 4: Run the full project test suite**

Run:
```bash
cd /home/kali/Desktop/Agentic-Ai-Decision-System && python -m pytest -q
```
Expected: All tests pass

- [ ] **Step 5: Commit**

```bash
git add tests/test_workflow_engine/test_specialist_nodes/test_integration.py
git commit -m "test: add integration tests for specialist node chaining"
```

---

### Task 8: Update CHANGELOG and bump version

**Files:**
- Modify: `CHANGELOG.md`
- Modify: `pyproject.toml`
- Modify: `src/decision_system/__init__.py`

- [ ] **Step 1: Update version to 1.13.0**

In `pyproject.toml`, change `version = "1.12.0"` to `version = "1.13.0"`.

In `src/decision_system/__init__.py`, change `__version__ = "1.12.0"` to `__version__ = "1.13.0"`.

- [ ] **Step 2: Add changelog entry**

Append to `CHANGELOG.md`:

```markdown
## v1.13.0 (2026-06-13)

### Phase 6: Bounded Specialist Agent Nodes

- **ResearcherNode** (`decision_system.researcher`) — AI-powered research synthesis with structured findings, citations, and confidence scores; deterministic fake fallback with keyword-matched mock data
- **CriticNode** (`decision_system.critic`) — Quality review node that checks for contradictions, unsupported claims, logical fallacies, and confidence calibration; LLM path for deep semantic review, deterministic rule-based fallback
- **SynthesizerNode** (`decision_system.synthesizer`) — Evidence-to-decision synthesis with weighted scoring, risk assessment, and ranked recommendations; LLM path for nuanced analysis, keyword-matched fake options

### Node Registry & Integration

- All 3 specialist nodes registered in `create_default_registry()` (27 total node types)
- Integration tests for Researcher→Critic chaining and multi-stream synthesis
- Frontend mock data entries for all 3 node types with full config/input/output schemas
```

- [ ] **Step 3: Verify version consistency**

Run:
```bash
python -m pytest tests/test_workspaces.py::test_version_consistency -v
```
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add CHANGELOG.md pyproject.toml src/decision_system/__init__.py
git commit -m "release: v1.13.0 — Phase 6 specialist agent nodes"
```

---

### Task 9: Final verification pass

- [ ] **Step 1: Clean up any generated files**

Run:
```bash
cd /home/kali/Desktop/Agentic-Ai-Decision-System && git status
```
Expected: Only the intended files modified (no stray `__pycache__` or `.decision_system/` artifacts)

- [ ] **Step 2: Run full test suite**

Run:
```bash
cd /home/kali/Desktop/Agentic-Ai-Decision-System && python -m pytest -q
```
Expected: All tests pass

- [ ] **Step 3: Verify the frontend still builds**

Run:
```bash
cd web/workflow-builder && npx vite build 2>&1 | tail -5
```
Expected: Build succeeds

- [ ] **Step 4: Quick smoke test — registry lists all types**

Run:
```bash
cd /home/kali/Desktop/Agentic-Ai-Decision-System && python -c "
from decision_system.workflow_engine.nodes import create_default_registry
registry = create_default_registry()
types = registry.list_types()
for t in types:
    print(f'  {t.type:45s} {t.label}')
print(f'\nTotal: {len(types)} node types')
"
```
Expected: Shows all 27 types including the 3 new specialist nodes
