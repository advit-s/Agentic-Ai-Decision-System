"""Ontology models for v0.4.

The ontology layer maps raw dataset columns to business concepts such as
revenue, expense, customer segment, marketing channel, complaint issue,
conversion rate, operational delay, and more. This enables detectors to
reason about data semantically rather than only by raw column name.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Typed enumerations
# ---------------------------------------------------------------------------

ConceptType = Literal["entity", "metric", "signal", "relationship", "risk", "process", "unknown"]

# ---------------------------------------------------------------------------
# OntologyConcept
# ---------------------------------------------------------------------------


class OntologyConcept(BaseModel):
    """A business concept in the ontology.

    Concepts represent high-level business ideas (revenue, expense, customer,
    risk, etc.) that raw dataset columns are mapped to.
    """

    concept_id: str
    name: str = Field(default="")
    description: str = Field(default="")
    concept_type: ConceptType = "unknown"
    aliases: list[str] = Field(default_factory=list)
    category: str = Field(default="", description="Optional business category tag")
    detector_hints: list[str] = Field(
        default_factory=list,
        description="Detectors that this concept is relevant to",
    )


# ---------------------------------------------------------------------------
# ColumnMapping
# ---------------------------------------------------------------------------


class ColumnMapping(BaseModel):
    """Maps a single dataset column to an ontology concept."""

    dataset_id: str = Field(description="Stable dataset identifier")
    source_filename: str = Field(description="Original CSV filename")
    category: str = Field(description="Data catalog category (e.g. financial)")
    column_name: str = Field(description="Raw column name in the CSV")
    mapped_concept_id: str = Field(description="Target ontology concept id")
    mapped_concept_name: str = Field(default="", description="Human-readable concept name")
    confidence: str = Field(default="high", description="high | medium | low")
    reason: str = Field(default="", description="Why this mapping was chosen")


# ---------------------------------------------------------------------------
# OntologyMap
# ---------------------------------------------------------------------------


class OntologyMap(BaseModel):
    """Container for the full ontology: concepts + column mappings."""

    concepts: list[OntologyConcept] = Field(default_factory=list)
    column_mappings: list[ColumnMapping] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # -- convenience helpers --------------------------------------------------

    def concept_by_id(self, concept_id: str) -> OntologyConcept | None:
        for c in self.concepts:
            if c.concept_id == concept_id:
                return c
        return None

    def mappings_for_dataset(self, dataset_id: str) -> list[ColumnMapping]:
        return [m for m in self.column_mappings if m.dataset_id == dataset_id]

    def mappings_for_concept(self, concept_id: str) -> list[ColumnMapping]:
        return [m for m in self.column_mappings if m.mapped_concept_id == concept_id]
