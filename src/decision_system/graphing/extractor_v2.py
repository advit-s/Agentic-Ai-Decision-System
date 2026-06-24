"""Deterministic entity, relationship, risk, and metric extraction v2.

This extractor uses rule-based patterns to extract structured intelligence
from evidence text without an LLM. Output includes workspace-scoped nodes,
edges, risks, and metrics with evidence references.

Extraction categories:
  - Entities: company, vendor, product, person, system, team, document
  - Financial: money amounts, percentages, currency values
  - Temporal: dates, time periods
  - Contact: emails, domains
  - Risks: risk phrases, security/compliance signals, financial signals
  - Metrics: named metrics with values (revenue, cost, count, rate)
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import datetime, timezone
from hashlib import sha1
from typing import Any

from decision_system.graphing.models import (
    EdgeType,
    NodeType,
    WorkspaceEdge,
    WorkspaceMetric,
    WorkspaceNode,
    WorkspaceRisk,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_CONFIDENCE = "medium"
DEFAULT_EXTRACTION_METHOD = "deterministic"

# Stopwords that should not be treated as entity names
STOPWORDS = frozenset({
    "the", "a", "an", "this", "that", "these", "those", "it", "its", "they",
    "them", "their", "we", "our", "you", "your", "he", "she", "his", "her",
    "and", "or", "but", "if", "because", "as", "until", "while", "of", "at",
    "by", "for", "with", "about", "against", "between", "into", "through",
    "during", "before", "after", "above", "below", "to", "from", "up", "down",
    "in", "out", "on", "off", "over", "under", "again", "further", "then",
    "once", "here", "there", "when", "where", "why", "how", "all", "each",
    "every", "both", "few", "more", "most", "other", "some", "such", "no",
    "nor", "not", "only", "own", "same", "so", "than", "too", "very",
    "just", "also", "has", "had", "have", "been", "being", "do", "does",
    "did", "doing", "would", "could", "should", "may", "might", "shall",
    "will", "can", "need", "dare", "must", "is", "am", "are", "was", "were",
    "be", "get", "got", "getting", "go", "goes", "went", "gone", "going",
    "make", "makes", "made", "making", "take", "takes", "took", "taken",
    "taking", "know", "knows", "knew", "known", "see", "sees", "saw", "seen",
    "thing", "things", "something", "nothing", "anything", "everything",
    "one", "two", "three", "first", "second", "third", "last", "next",
    "previous", "current", "new", "old", "top", "bottom", "high", "low",
    "big", "small", "large", "long", "short", "full", "empty", "good",
    "bad", "better", "best", "worst", "worse", "right", "wrong", "true",
    "false", "real", "actual", "possible", "whole", "certain", "various",
    "different", "important", "significant", "major", "minor", "key",
    "main", "primary", "secondary", "additional", "single", "multiple",
    "simple", "complex", "open", "closed", "public", "private", "direct",
    "indirect", "total", "partial", "annual", "monthly", "weekly", "daily",
    "quarterly", "current", "previous", "upcoming", "recent", "latest",
})

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# Money: $X, USD X, €X, £X, X USD, X EUR
MONEY_PATTERN = re.compile(
    r"(?:\$|USD\s?|€|£|EUR\s?|GBP\s?|CAD\s?|AUD\s?)"
    r"\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?"
    r"|\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?\s*(?:USD|EUR|GBP|CAD|AUD)",
    re.IGNORECASE,
)

# Percentage: X%, X percent
PERCENTAGE_PATTERN = re.compile(
    r"\d+(?:\.\d+)?\s*%|\d+(?:\.\d+)?\s*percent",
    re.IGNORECASE,
)

# Dates: ISO dates, US dates, month name dates
DATE_PATTERN = re.compile(
    r"\d{4}-\d{2}-\d{2}"  # 2026-06-23
    r"|\d{2}/\d{2}/\d{4}"  # 06/23/2026
    r"|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}"
    r"|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}",
)

# Email and domain
EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
DOMAIN_PATTERN = re.compile(
    r"(?:https?://)?(?:www\.)?([a-zA-Z0-9-]+\.(?:com|org|net|io|gov|edu|co|uk|ai|app|dev))",
    re.IGNORECASE,
)

# Risk phrases
RISK_PATTERNS: list[tuple[str, str, str]] = [
    # (category, severity, phrase_pattern)
    ("security", "high", r"(?:security|cyber|data)\s*(?:breach|incident|attack|vulnerability|leak|exploit)"),
    ("security", "high", r"(?:unauthorized|malicious|ransomware|phishing)"),
    ("compliance", "high", r"(?:regulatory|compliance|gdpr|hipaa|sox|pci)\s*(?:risk|violation|non-?compliance|audit)"),
    ("financial", "high", r"(?:revenue\s+loss|profit\s+(?:decline|drop)|liquidity|cash\s+(?:flow|crunch))"),
    ("financial", "medium", r"(?:cost\s+overrun|budget\s+(?:overage|shortfall)|margin\s+(?:erosion|decline))"),
    ("vendor", "high", r"(?:vendor\s+(?:risk|lock-?in|failure|bankruptcy|concentration))"),
    ("vendor", "medium", r"(?:supply\s+chain\s+(?:disruption|risk|delay|bottleneck))"),
    ("operational", "high", r"(?:service\s+outage|downtime|system\s+failure|disaster\s+recovery)"),
    ("operational", "medium", r"(?:bottleneck|delay|backlog|attrition|turnover)"),
    ("technical", "medium", r"(?:technical\s+debt|legacy\s+system|migration\s+risk|integration\s+challenge)"),
    ("technical", "high", r"(?:single\s+point\s+of\s+failure|no\s+(?:fallback|redundancy|backup))"),
    ("strategic", "medium", r"(?:market\s+(?:decline|saturation|risk)|competitive\s+(?:threat|pressure|risk))"),
]

# Metric keywords
METRIC_KEYWORDS = [
    "revenue", "cost", "profit", "margin", "expense", "budget",
    "customer", "user", "employee", "vendor", "partner",
    "count", "rate", "percentage", "ratio", "average",
    "growth", "decline", "increase", "decrease", "change",
    "revenue_run_rate", "arr", "mrr", "churn", "ltv", "cac",
    "nps", "csat", "sla", "kpi", "roi", "roas",
]

# Company name suffixes
COMPANY_SUFFIXES = [
    "corp", "corporation", "inc", "incorporated", "ltd", "limited",
    "llc", "lp", "gmbh", "ag", "sa", "pty", "plc", "co",
]

# Industry/company keywords
COMPANY_KEYWORDS = [
    "technologies", "solutions", "systems", "software", "services",
    "group", "ventures", "partners", "holdings", "enterprises",
    "global", "digital", "analytics", "ai", "cloud", "data",
]

# Entity type inference
ENTITY_TYPE_HINTS: list[tuple[re.Pattern, NodeType]] = [
    (re.compile(r"\b(?:team|group|department|division|squad)\b", re.IGNORECASE), "team"),
    (re.compile(r"\b(?:vendor|supplier|provider|partner)\b", re.IGNORECASE), "vendor"),
    (re.compile(r"\b(?:customer|client|buyer)\b", re.IGNORECASE), "customer"),
    (re.compile(r"\b(?:product|platform|solution)\b", re.IGNORECASE), "product"),
    (re.compile(r"\b(?:system|service|api|tool|app|application)\b", re.IGNORECASE), "system"),
    (re.compile(r"\b(?:ceo|cto|cfo|director|manager|lead|engineer)\b", re.IGNORECASE), "person"),
]

# Relationship patterns
RELATION_PATTERNS: list[tuple[EdgeType, re.Pattern]] = [
    ("depends_on", re.compile(r"(?P<source>.+?)\s+depends on\s+(?P<target>.+)", re.IGNORECASE)),
    ("owns", re.compile(r"(?P<source>.+?)\s+(?:is\s+)?owned by\s+(?P<target>.+)", re.IGNORECASE)),
    ("supplies", re.compile(r"(?P<source>.+?)\s+(?:supplies?|provides?|offers?)\s+(?P<target>.+)", re.IGNORECASE)),
    ("affects", re.compile(r"(?P<source>.+?)\s+affects?\s+(?P<target>.+)", re.IGNORECASE)),
    ("contradicts", re.compile(r"CONTRADICTS:\s*(?P<target>[^.!?\n]+)", re.IGNORECASE)),
    ("related_to", re.compile(r"(?P<source>.+?)\s+(?:(?:is|are)\s+)?related to\s+(?P<target>.+)", re.IGNORECASE)),
    ("mentions", re.compile(r"(?P<source>.+?)\s+references?\s+(?P<target>.+)", re.IGNORECASE)),
]


# ---------------------------------------------------------------------------
# Extraction result container
# ---------------------------------------------------------------------------


class ExtractionResult:
    """Container for all extracted intelligence from a batch of evidence."""

    def __init__(self, workspace_id: str | None = None):
        self.workspace_id = workspace_id or "default"
        self.nodes: dict[str, WorkspaceNode] = {}
        self.edges: dict[str, WorkspaceEdge] = {}
        self.risks: dict[str, WorkspaceRisk] = {}
        self.metrics: dict[str, WorkspaceMetric] = {}
        self.warnings: list[str] = []

    def to_node_list(self) -> list[WorkspaceNode]:
        return sorted(self.nodes.values(), key=lambda n: n.node_id)

    def to_edge_list(self) -> list[WorkspaceEdge]:
        return sorted(self.edges.values(), key=lambda e: e.edge_id)

    def to_risk_list(self) -> list[WorkspaceRisk]:
        return sorted(self.risks.values(), key=lambda r: r.risk_id)

    def to_metric_list(self) -> list[WorkspaceMetric]:
        return sorted(self.metrics.values(), key=lambda m: m.metric_id)


# ---------------------------------------------------------------------------
# Main extraction function
# ---------------------------------------------------------------------------


def extract_intelligence(
    texts: Iterable[tuple[str, str, str, str]],
    workspace_id: str = "default",
) -> ExtractionResult:
    """Extract entities, relationships, risks, and metrics from evidence texts.

    Args:
        texts: Iterable of (text, evidence_id, source_id, chunk_id) tuples.
        workspace_id: Target workspace for extracted items.

    Returns:
        ExtractionResult with nodes, edges, risks, and metrics.
    """
    result = ExtractionResult(workspace_id)

    for text, evidence_id, source_id, chunk_id in texts:
        source_info = {
            "evidence_ids": [evidence_id] if evidence_id else [],
            "source_ids": [source_id] if source_id else [],
            "chunk_ids": [chunk_id] if chunk_id else [],
        }

        # Extract entities
        _extract_companies(text, result, source_info)
        _extract_vendors(text, result, source_info)
        _extract_products(text, result, source_info)
        _extract_named_entities(text, result, source_info)

        # Extract financial
        _extract_money(text, result, source_info)
        _extract_percentages(text, result, source_info)

        # Extract temporal
        _extract_dates(text, result, source_info)
        _extract_emails_and_domains(text, result, source_info)

        # Extract risks
        _extract_risks(text, result, source_info)

        # Extract metrics
        _extract_metrics(text, result, source_info)

        # Extract relationships
        _extract_relationships(text, result, source_info)

    return result


# ---------------------------------------------------------------------------
# Entity extraction helpers
# ---------------------------------------------------------------------------


def _normalize_name(name: str) -> str:
    return re.sub(r"\s+", " ", name).strip().lower()


def _make_id(prefix: str, name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:64]
    if not slug:
        slug = sha1(name.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{slug}"


def _upsert_node(
    result: ExtractionResult,
    name: str,
    node_type: NodeType,
    source_info: dict[str, Any],
) -> WorkspaceNode:
    """Add or update a node in the result."""
    node_id = _make_id("node", name)
    existing = result.nodes.get(node_id)
    now = datetime.now(timezone.utc)

    if existing:
        existing.evidence_ids = _with_unique(existing.evidence_ids, source_info.get("evidence_ids", []))
        existing.source_ids = _with_unique(existing.source_ids, source_info.get("source_ids", []))
        existing.chunk_ids = _with_unique(existing.chunk_ids, source_info.get("chunk_ids", []))
        existing.updated_at = now
        return existing

    node = WorkspaceNode(
        node_id=node_id,
        workspace_id=result.workspace_id,
        node_type=node_type,
        name=name,
        normalized_name=_normalize_name(name),
        confidence=DEFAULT_CONFIDENCE,
        status="extracted",
        evidence_ids=source_info.get("evidence_ids", []),
        source_ids=source_info.get("source_ids", []),
        chunk_ids=source_info.get("chunk_ids", []),
        metadata={"extraction_method": DEFAULT_EXTRACTION_METHOD},
        created_at=now,
        updated_at=now,
    )
    result.nodes[node_id] = node
    return node


def _with_unique(
    existing: list[str],
    new: list[str],
) -> list[str]:
    """Merge new values into existing list, preserving order and uniqueness."""
    seen = set(existing)
    return existing + [v for v in new if v not in seen]


def _infer_entity_type(name: str) -> NodeType:
    """Infer entity type from name content."""
    lower = name.lower()
    for pattern, ntype in ENTITY_TYPE_HINTS:
        if pattern.search(lower):
            return ntype
    return "unknown"


def _clean_phrase(text: str) -> str:
    """Clean up a matched entity phrase."""
    text = re.sub(r"\s+", " ", text).strip()
    text = text.strip(" .,:;!?\"'`()[]{}")
    text = re.sub(r"^(?:the|a|an)\s+", "", text, flags=re.IGNORECASE)
    return text[:160].strip()


def _sentences(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", text).strip()
    return [
        s.strip()
        for s in re.split(r"(?<=[.!?])\s+", normalized)
        if s.strip()
    ]


# ---------------------------------------------------------------------------
# Company name extraction
# ---------------------------------------------------------------------------


def _extract_companies(text: str, result: ExtractionResult, source_info: dict[str, Any]) -> None:
    """Extract company names using suffix/keyword patterns."""
    suffix_pattern = r"\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)\s+(" + "|".join(COMPANY_SUFFIXES) + r")\.?"
    for match in re.finditer(suffix_pattern, text, re.IGNORECASE):
        name = _clean_phrase(match.group(0).rstrip("."))
        if len(name) > 2:
            _upsert_node(result, name, "company", source_info)

    # Capitalized multi-word phrases followed by company keywords
    keyword_pattern = r"\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*(?:\s+(" + "|".join(COMPANY_KEYWORDS) + r")))\.?"
    for match in re.finditer(keyword_pattern, text, re.IGNORECASE):
        name = _clean_phrase(match.group(0).rstrip("."))
        if len(name) > 3:
            _upsert_node(result, name, "company", source_info)


def _extract_vendors(text: str, result: ExtractionResult, source_info: dict[str, Any]) -> None:
    """Extract vendor names from explicit vendor references."""
    patterns = [
        r"(?:vendor|supplier|provider)\s+(?:called|named|known as)?\s*[:\-]?\s*([A-Z][A-Za-z0-9]+(?:\s+[A-Z][A-Za-z0-9]+)*)",
        r"([A-Z][A-Za-z0-9]+(?:\s+[A-Z][A-Za-z0-9]+)*)\s+(?:is\s+(?:a\s+)?(?:vendor|supplier|provider))",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            name = _clean_phrase(match.group(1))
            if len(name) > 2:
                _upsert_node(result, name, "vendor", source_info)


def _extract_products(text: str, result: ExtractionResult, source_info: dict[str, Any]) -> None:
    """Extract product names."""
    patterns = [
        r"(?:product|platform|solution|service)\s+(?:called|named|known as)?\s*[:\-]?\s*([A-Z][A-Za-z0-9]+(?:\s+[A-Z][A-Za-z0-9]+)*)",
        r"([A-Z][A-Za-z0-9]+(?:\s+[A-Z][A-Za-z0-9]+)*)\s+(?:is\s+(?:a\s+)?(?:product|platform|solution|service))",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            name = _clean_phrase(match.group(1))
            if len(name) > 2:
                _upsert_node(result, name, "product", source_info)


def _extract_named_entities(text: str, result: ExtractionResult, source_info: dict[str, Any]) -> None:
    """Extract general named entities (capitalized phrases) and infer types."""
    # Look for capitalized multi-word phrases that might be entities
    for sentence in _sentences(text):
        # Skip if already processed by specific extractors
        entities = re.findall(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,4})\b", sentence)
        for name in entities:
            name = _clean_phrase(name)
            if len(name) < 3:
                continue
            node_id = _make_id("node", name)
            if node_id in result.nodes:
                continue
            etype = _infer_entity_type(name)
            _upsert_node(result, name, etype, source_info)


# ---------------------------------------------------------------------------
# Financial extraction
# ---------------------------------------------------------------------------


def _extract_money(text: str, result: ExtractionResult, source_info: dict[str, Any]) -> None:
    """Extract money amounts as metrics."""
    for match in MONEY_PATTERN.finditer(text):
        value = match.group(0).strip()
        metric_id = _make_id("metric", f"money-{value}")
        if metric_id in result.metrics:
            continue
        now = datetime.now(timezone.utc)
        metric = WorkspaceMetric(
            metric_id=metric_id,
            workspace_id=result.workspace_id,
            name="Monetary Amount",
            value=value,
            unit="USD",
            confidence=DEFAULT_CONFIDENCE,
            status="extracted",
            evidence_ids=source_info.get("evidence_ids", []),
            source_ids=source_info.get("source_ids", []),
            chunk_ids=source_info.get("chunk_ids", []),
            metadata={"extraction_method": DEFAULT_EXTRACTION_METHOD},
            created_at=now,
            updated_at=now,
        )
        result.metrics[metric_id] = metric


def _extract_percentages(text: str, result: ExtractionResult, source_info: dict[str, Any]) -> None:
    """Extract percentages as metrics."""
    for match in PERCENTAGE_PATTERN.finditer(text):
        value = match.group(0).strip()
        metric_id = _make_id("metric", f"pct-{value}")
        if metric_id in result.metrics:
            continue
        now = datetime.now(timezone.utc)
        metric = WorkspaceMetric(
            metric_id=metric_id,
            workspace_id=result.workspace_id,
            name="Percentage",
            value=value,
            unit="%",
            confidence=DEFAULT_CONFIDENCE,
            status="extracted",
            evidence_ids=source_info.get("evidence_ids", []),
            source_ids=source_info.get("source_ids", []),
            chunk_ids=source_info.get("chunk_ids", []),
            metadata={"extraction_method": DEFAULT_EXTRACTION_METHOD},
            created_at=now,
            updated_at=now,
        )
        result.metrics[metric_id] = metric


# ---------------------------------------------------------------------------
# Temporal extraction
# ---------------------------------------------------------------------------


def _extract_dates(text: str, result: ExtractionResult, source_info: dict[str, Any]) -> None:
    """Extract dates as event nodes."""
    for match in DATE_PATTERN.finditer(text):
        date_str = match.group(0).strip()
        node_id = _make_id("node", f"date-{date_str}")
        if node_id in result.nodes:
            continue
        now = datetime.now(timezone.utc)
        node = WorkspaceNode(
            node_id=node_id,
            workspace_id=result.workspace_id,
            node_type="event",
            name=f"Date: {date_str}",
            normalized_name=date_str,
            description=f"Date reference found in evidence: {date_str}",
            confidence="low",
            status="extracted",
            evidence_ids=source_info.get("evidence_ids", []),
            source_ids=source_info.get("source_ids", []),
            chunk_ids=source_info.get("chunk_ids", []),
            metadata={
                "extraction_method": DEFAULT_EXTRACTION_METHOD,
                "date_value": date_str,
            },
            created_at=now,
            updated_at=now,
        )
        result.nodes[node_id] = node


# ---------------------------------------------------------------------------
# Contact extraction
# ---------------------------------------------------------------------------


def _extract_emails_and_domains(text: str, result: ExtractionResult, source_info: dict[str, Any]) -> None:
    """Extract email addresses and domain names as entities."""
    for match in EMAIL_PATTERN.finditer(text):
        email = match.group(0).strip()
        node_id = _make_id("node", f"email-{email}")
        if node_id in result.nodes:
            continue
        now = datetime.now(timezone.utc)
        node = WorkspaceNode(
            node_id=node_id,
            workspace_id=result.workspace_id,
            node_type="unknown",
            name=email,
            normalized_name=email.lower(),
            description=f"Email address: {email}",
            confidence="low",
            status="extracted",
            evidence_ids=source_info.get("evidence_ids", []),
            source_ids=source_info.get("source_ids", []),
            chunk_ids=source_info.get("chunk_ids", []),
            metadata={
                "extraction_method": DEFAULT_EXTRACTION_METHOD,
                "contact_type": "email",
            },
            created_at=now,
            updated_at=now,
        )
        result.nodes[node_id] = node


# ---------------------------------------------------------------------------
# Risk extraction
# ---------------------------------------------------------------------------


def _extract_risks(text: str, result: ExtractionResult, source_info: dict[str, Any]) -> None:
    """Extract risks from text using risk phrase patterns."""
    for category, severity, pattern_str in RISK_PATTERNS:
        pattern = re.compile(pattern_str, re.IGNORECASE)
        for match in pattern.finditer(text):
            matched_text = match.group(0).strip()
            risk_id = _make_id("risk", matched_text)
            if risk_id in result.risks:
                continue

            # Find the surrounding sentence for context
            context = ""
            for sentence in _sentences(text):
                if matched_text.lower() in sentence.lower():
                    context = sentence[:200]
                    break

            now = datetime.now(timezone.utc)
            risk = WorkspaceRisk(
                risk_id=risk_id,
                workspace_id=result.workspace_id,
                title=f"Risk: {matched_text}",
                description=context or f"Detected risk phrase: {matched_text}",
                severity=severity,  # type: ignore[arg-type]
                category=category,  # type: ignore[arg-type]
                confidence=DEFAULT_CONFIDENCE,
                status="extracted",
                evidence_ids=source_info.get("evidence_ids", []),
                source_ids=source_info.get("source_ids", []),
                chunk_ids=source_info.get("chunk_ids", []),
                metadata={"extraction_method": DEFAULT_EXTRACTION_METHOD},
                created_at=now,
                updated_at=now,
            )
            result.risks[risk_id] = risk


# ---------------------------------------------------------------------------
# Metric extraction
# ---------------------------------------------------------------------------


def _extract_metrics(text: str, result: ExtractionResult, source_info: dict[str, Any]) -> None:
    """Extract named metrics with values from text."""
    # Pattern: <metric_name>: <value> or <metric_name> is <value>
    for sentence in _sentences(text):
        for keyword in METRIC_KEYWORDS:
            kw_pattern = re.compile(
                rf"\b{keyword}\b.{{0,80}}?\s*(\$?[\d,]+(?:\.[\d]+)?(?:\s*[%USDKEurMNBmk]{{1,6}})?)\b",
                re.IGNORECASE,
            )
            for match in kw_pattern.finditer(sentence):
                raw_value = match.group(1)
                if raw_value is None:
                    continue
                value = raw_value.strip()
                metric_id = _make_id("metric", f"{keyword}-{value}")
                if metric_id in result.metrics:
                    continue
                now = datetime.now(timezone.utc)
                metric = WorkspaceMetric(
                    metric_id=metric_id,
                    workspace_id=result.workspace_id,
                    name=keyword.capitalize(),
                    value=value,
                    unit=_infer_unit(value),
                    confidence=DEFAULT_CONFIDENCE,
                    status="extracted",
                    evidence_ids=source_info.get("evidence_ids", []),
                    source_ids=source_info.get("source_ids", []),
                    chunk_ids=source_info.get("chunk_ids", []),
                    metadata={"extraction_method": DEFAULT_EXTRACTION_METHOD},
                    created_at=now,
                    updated_at=now,
                )
                result.metrics[metric_id] = metric


def _infer_unit(value: str) -> str:
    """Infer the unit from a metric value string."""
    value = value.strip()
    if value.endswith("%"):
        return "%"
    if value.startswith("$"):
        return "USD"
    if value.upper().endswith("USD"):
        return "USD"
    if value.upper().endswith("K"):
        return "thousands"
    if value.upper().endswith("M"):
        return "millions"
    return "count"


# ---------------------------------------------------------------------------
# Relationship extraction
# ---------------------------------------------------------------------------


def _extract_relationships(text: str, result: ExtractionResult, source_info: dict[str, Any]) -> None:
    """Extract relationships between known entities."""
    for sentence in _sentences(text):
        # Check for contradiction marker first
        contradiction_match = re.search(r"CONTRADICTS:\s*(?P<target>[^.!?\n]+)", sentence, re.IGNORECASE)
        if contradiction_match:
            target = _clean_phrase(contradiction_match.group("target"))
            _add_relationship(result, "Contradiction marker", target, "contradicts", source_info)
            continue

        for edge_type, pattern in RELATION_PATTERNS:
            if edge_type == "contradicts":
                continue  # handled above
            match = pattern.search(sentence)
            if not match:
                continue
            source_name = _clean_phrase(match.group("source"))
            target_name = _clean_phrase(match.group("target"))
            if source_name and target_name:
                _add_relationship(result, source_name, target_name, edge_type, source_info)
            break


def _add_relationship(
    result: ExtractionResult,
    source_name: str,
    target_name: str,
    edge_type: EdgeType,
    source_info: dict[str, Any],
) -> None:
    """Add or update a relationship between two entities."""
    # Ensure both entities exist
    source_node = _upsert_node(result, source_name, _infer_entity_type(source_name), source_info)
    target_node = _upsert_node(result, target_name, _infer_entity_type(target_name), source_info)

    edge_id = _make_id("edge", f"{source_node.node_id}-{edge_type}-{target_node.node_id}")
    existing = result.edges.get(edge_id)
    now = datetime.now(timezone.utc)

    if existing:
        existing.evidence_ids = _with_unique(existing.evidence_ids, source_info.get("evidence_ids", []))
        existing.source_ids = _with_unique(existing.source_ids, source_info.get("source_ids", []))
        existing.chunk_ids = _with_unique(existing.chunk_ids, source_info.get("chunk_ids", []))
        existing.updated_at = now
        return

    edge = WorkspaceEdge(
        edge_id=edge_id,
        workspace_id=result.workspace_id,
        source_node_id=source_node.node_id,
        target_node_id=target_node.node_id,
        edge_type=edge_type,
        label=edge_type.replace("_", " "),
        confidence=DEFAULT_CONFIDENCE,
        status="extracted",
        evidence_ids=source_info.get("evidence_ids", []),
        source_ids=source_info.get("source_ids", []),
        chunk_ids=source_info.get("chunk_ids", []),
        metadata={"extraction_method": DEFAULT_EXTRACTION_METHOD},
        created_at=now,
        updated_at=now,
    )
    result.edges[edge_id] = edge
