"""Ontology sub-package for v0.4.

Maps raw dataset columns to business concepts such as revenue, expense,
customer segment, marketing channel, complaint issue, and more.
"""

from decision_system.ontology.models import (
    ColumnMapping,
    ConceptType,
    OntologyConcept,
    OntologyMap,
)
from decision_system.ontology.store import (
    DEFAULT_ONTOLOGY_DIR,
    DEFAULT_ONTOLOGY_FILENAME,
    _ontology_path,
    load_ontology,
    save_ontology,
)

__all__ = [
    "ColumnMapping",
    "ConceptType",
    "OntologyConcept",
    "OntologyMap",
    "DEFAULT_ONTOLOGY_DIR",
    "DEFAULT_ONTOLOGY_FILENAME",
    "load_ontology",
    "save_ontology",
    "_ontology_path",
]
