"""Typed models for the local company knowledge graph.

The v0.2 graph is intentionally a JSON-serializable local structure rather
than a database. It records entities, relationships, and their source evidence
so future pattern detection can stay auditable.
"""

from typing import Literal

from pydantic import BaseModel, Field

from decision_system.models import ConfidenceLevel


EntityType = Literal[
    "project",
    "system",
    "team",
    "person",
    "vendor",
    "customer",
    "incident",
    "risk",
    "decision",
    "technology",
    "unknown",
]

RelationType = Literal[
    "depends_on",
    "owned_by",
    "caused",
    "affects",
    "blocks",
    "mitigates",
    "contradicts",
    "related_to",
]


class Entity(BaseModel):
    """A company object mentioned in indexed evidence."""

    entity_id: str
    name: str
    entity_type: EntityType
    source_evidence_ids: list[str] = Field(default_factory=list)
    source_filenames: list[str] = Field(default_factory=list)
    confidence: ConfidenceLevel


class Relationship(BaseModel):
    """A directed relationship between two extracted entities."""

    relationship_id: str
    source_entity_id: str
    relation_type: RelationType
    target_entity_id: str
    source_evidence_ids: list[str] = Field(default_factory=list)
    source_filenames: list[str] = Field(default_factory=list)
    confidence: ConfidenceLevel


class KnowledgeGraph(BaseModel):
    """Local graph-like JSON store for extracted company intelligence."""

    entities: list[Entity] = Field(default_factory=list)
    relationships: list[Relationship] = Field(default_factory=list)
