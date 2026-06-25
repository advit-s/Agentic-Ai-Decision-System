"""Persist and load the ontology map as JSON."""

from __future__ import annotations

import json
from pathlib import Path

from decision_system._data_root import get_data_root
from decision_system.ontology.models import OntologyMap


def _default_ontology_dir() -> Path:
    return get_data_root() / "ontology"


DEFAULT_ONTOLOGY_FILENAME = "ontology_map.json"


def _ontology_path(store_dir: Path | str | None = None) -> Path:
    """Return the on-disk path for the ontology map JSON file."""
    if store_dir is None:
        store_dir = _default_ontology_dir()
    return Path(store_dir) / DEFAULT_ONTOLOGY_FILENAME


def save_ontology(omap: OntologyMap, store_dir: Path | str | None = None) -> Path:
    """Write the ontology map to ``.decision_system/ontology/ontology_map.json``."""
    if store_dir is None:
        store_dir = _default_ontology_dir()
    path = _ontology_path(store_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(omap.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )
    return path.resolve()


def load_ontology(store_dir: Path | str | None = None) -> OntologyMap:
    """Load an ontology map from disk, returning an empty map on miss."""
    if store_dir is None:
        store_dir = _default_ontology_dir()
    path = _ontology_path(store_dir)
    if not path.exists():
        return OntologyMap()
    raw = json.loads(path.read_text(encoding="utf-8"))
    return OntologyMap.model_validate(raw)
