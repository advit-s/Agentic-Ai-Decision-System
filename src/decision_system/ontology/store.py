"""Persist and load the ontology map as JSON."""

from __future__ import annotations

import json
from pathlib import Path

from decision_system.ontology.models import OntologyMap

DEFAULT_ONTOLOGY_DIR = Path(".decision_system") / "ontology"
DEFAULT_ONTOLOGY_FILENAME = "ontology_map.json"


def _ontology_path(store_dir: Path | str = DEFAULT_ONTOLOGY_DIR) -> Path:
    """Return the on-disk path for the ontology map JSON file."""
    return Path(store_dir) / DEFAULT_ONTOLOGY_FILENAME


def save_ontology(omap: OntologyMap, store_dir: Path | str = DEFAULT_ONTOLOGY_DIR) -> Path:
    """Write the ontology map to ``.decision_system/ontology/ontology_map.json``."""
    path = _ontology_path(store_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(omap.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )
    return path.resolve()


def load_ontology(store_dir: Path | str = DEFAULT_ONTOLOGY_DIR) -> OntologyMap:
    """Load an ontology map from disk, returning an empty map on miss."""
    path = _ontology_path(store_dir)
    if not path.exists():
        return OntologyMap()
    raw = json.loads(path.read_text(encoding="utf-8"))
    return OntologyMap.model_validate(raw)
