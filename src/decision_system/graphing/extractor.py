"""Deterministic entity and relationship extraction for v0.2.

This extractor deliberately uses simple rules instead of an LLM. The goal is
stable offline behavior for early graph inspection and tests.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from hashlib import sha1

from decision_system.graphing.models import Entity, EntityType, KnowledgeGraph, Relationship, RelationType
from decision_system.models import EvidenceChunk


_RELATION_PATTERNS: list[tuple[RelationType, re.Pattern[str]]] = [
    (
        "depends_on",
        re.compile(r"(?P<source>.+?)\s+depends on\s+(?P<target>.+)", re.IGNORECASE),
    ),
    (
        "owned_by",
        re.compile(r"(?P<source>.+?)\s+(?:is\s+)?owned by\s+(?P<target>.+)", re.IGNORECASE),
    ),
    ("caused", re.compile(r"(?P<source>.+?)\s+caused\s+(?P<target>.+)", re.IGNORECASE)),
    ("affects", re.compile(r"(?P<source>.+?)\s+affects\s+(?P<target>.+)", re.IGNORECASE)),
    ("blocks", re.compile(r"(?P<source>.+?)\s+blocks\s+(?P<target>.+)", re.IGNORECASE)),
    (
        "mitigates",
        re.compile(r"(?P<source>.+?)\s+mitigates\s+(?P<target>.+)", re.IGNORECASE),
    ),
    (
        "related_to",
        re.compile(
            r"(?P<source>.+?)\s+(?:(?:is|are)\s+)?related to\s+(?P<target>.+)",
            re.IGNORECASE,
        ),
    ),
]

_CONTRADICTION_PATTERN = re.compile(
    r"CONTRADICTS:\s*(?P<target>[^.!?\n]+)",
    re.IGNORECASE,
)


def extract_knowledge_graph(chunks: Iterable[EvidenceChunk]) -> KnowledgeGraph:
    """Extract a deterministic knowledge graph from evidence chunks."""

    entities: dict[str, Entity] = {}
    relationships: dict[tuple[str, RelationType, str], Relationship] = {}

    for chunk in chunks:
        for source_name, relation_type, target_name in _extract_relationship_mentions(chunk.text):
            source_entity = _upsert_entity(entities, source_name, chunk)
            target_entity = _upsert_entity(entities, target_name, chunk)
            _upsert_relationship(
                relationships,
                source_entity.entity_id,
                relation_type,
                target_entity.entity_id,
                chunk,
            )

    return KnowledgeGraph(
        entities=sorted(entities.values(), key=lambda entity: entity.entity_id),
        relationships=sorted(
            relationships.values(),
            key=lambda relationship: relationship.relationship_id,
        ),
    )


def _extract_relationship_mentions(text: str) -> list[tuple[str, RelationType, str]]:
    mentions: list[tuple[str, RelationType, str]] = []
    mentions.extend(_extract_contradiction_mentions(text))

    for sentence in _sentences(text):
        if "CONTRADICTS:" in sentence.upper():
            continue
        for relation_type, pattern in _RELATION_PATTERNS:
            match = pattern.search(sentence)
            if not match:
                continue
            source_name = _clean_entity_phrase(match.group("source"))
            target_name = _clean_entity_phrase(match.group("target"))
            if source_name and target_name:
                mentions.append((source_name, relation_type, target_name))
            break

    return mentions


def _extract_contradiction_mentions(text: str) -> list[tuple[str, RelationType, str]]:
    mentions: list[tuple[str, RelationType, str]] = []
    for match in _CONTRADICTION_PATTERN.finditer(text):
        source_name = _previous_sentence(text[: match.start()]) or "Contradiction marker"
        target_name = _clean_entity_phrase(match.group("target"))
        if target_name:
            mentions.append((source_name, "contradicts", target_name))
    return mentions


def _upsert_entity(
    entities: dict[str, Entity],
    name: str,
    chunk: EvidenceChunk,
) -> Entity:
    entity_id = _entity_id(name)
    entity_type = _infer_entity_type(name)
    entity = entities.get(entity_id)

    if entity is None:
        entity = Entity(
            entity_id=entity_id,
            name=name,
            entity_type=entity_type,
            source_evidence_ids=[chunk.evidence_id],
            source_filenames=[chunk.source_filename],
            confidence="medium",
        )
        entities[entity_id] = entity
        return entity

    entity.source_evidence_ids = _with_unique(entity.source_evidence_ids, chunk.evidence_id)
    entity.source_filenames = _with_unique(entity.source_filenames, chunk.source_filename)
    if entity.entity_type == "unknown" and entity_type != "unknown":
        entity.entity_type = entity_type
    return entity


def _upsert_relationship(
    relationships: dict[tuple[str, RelationType, str], Relationship],
    source_entity_id: str,
    relation_type: RelationType,
    target_entity_id: str,
    chunk: EvidenceChunk,
) -> Relationship:
    relationship_key = (source_entity_id, relation_type, target_entity_id)
    relationship = relationships.get(relationship_key)

    if relationship is None:
        relationship = Relationship(
            relationship_id=_relationship_id(source_entity_id, relation_type, target_entity_id),
            source_entity_id=source_entity_id,
            relation_type=relation_type,
            target_entity_id=target_entity_id,
            source_evidence_ids=[chunk.evidence_id],
            source_filenames=[chunk.source_filename],
            confidence="medium",
        )
        relationships[relationship_key] = relationship
        return relationship

    relationship.source_evidence_ids = _with_unique(
        relationship.source_evidence_ids,
        chunk.evidence_id,
    )
    relationship.source_filenames = _with_unique(
        relationship.source_filenames,
        chunk.source_filename,
    )
    return relationship


def _sentences(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", text).strip()
    return [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", normalized)
        if sentence.strip()
    ]


def _previous_sentence(prefix: str) -> str:
    sentences = _sentences(prefix)
    if not sentences:
        return ""
    return _clean_entity_phrase(sentences[-1])


def _clean_entity_phrase(value: str) -> str:
    value = re.sub(r"\s+", " ", value).strip()
    value = value.strip(" .,:;!?\"'`()[]{}")
    value = re.sub(r"^(?:the|a|an)\s+", "", value, flags=re.IGNORECASE)
    return value[:160].strip()


def _entity_id(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if not slug:
        slug = sha1(name.encode("utf-8")).hexdigest()[:12]
    return f"entity-{slug[:80]}"


def _relationship_id(
    source_entity_id: str,
    relation_type: RelationType,
    target_entity_id: str,
) -> str:
    digest = sha1(
        f"{source_entity_id}|{relation_type}|{target_entity_id}".encode("utf-8")
    ).hexdigest()[:12]
    return f"relationship-{relation_type}-{digest}"


def _infer_entity_type(name: str) -> EntityType:
    lower_name = name.lower()
    if "team" in lower_name:
        return "team"
    if "vendor" in lower_name:
        return "vendor"
    if "customer" in lower_name or "client" in lower_name:
        return "customer"
    if "incident" in lower_name or "outage" in lower_name:
        return "incident"
    if "risk" in lower_name or "failure" in lower_name or "vulnerability" in lower_name:
        return "risk"
    if "decision" in lower_name:
        return "decision"
    if "project" in lower_name or "migration" in lower_name:
        return "project"
    if "system" in lower_name or "service" in lower_name or "auth" in lower_name:
        return "system"
    if any(term in lower_name for term in ("python", "chroma", "langgraph", "api")):
        return "technology"
    return "unknown"


def _with_unique(values: list[str], value: str) -> list[str]:
    if value in values:
        return values
    return [*values, value]
