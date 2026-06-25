"""Persist and load local CSV profile summaries as JSON."""

from __future__ import annotations

import json
from pathlib import Path

from decision_system._data_root import get_data_root
from decision_system.data_catalog.loader import LoadedDataset, load_csv
from decision_system.data_catalog.models import (
    ALL_CATEGORIES,
    DataProfileStore,
    DatasetProfile,
)
from decision_system.data_catalog.profiler import profile_dataset


def _default_store_dir() -> Path:
    return get_data_root()


PROFILE_DIRNAME = "data_profiles"
PROFILES_FILENAME = "profiles.json"


def _profiles_path(store_dir: Path | str | None = None) -> Path:
    """Return the on-disk path for the profiles JSON file."""

    if store_dir is None:
        store_dir = _default_store_dir()
    return Path(store_dir) / PROFILE_DIRNAME / PROFILES_FILENAME


def save_profiles(store: DataProfileStore, store_dir: Path | str | None = None) -> Path:
    """Write the profile store to `.decision_system/data_profiles/profiles.json`."""

    path = _profiles_path(store_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(store.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )
    return path.resolve()


def load_profiles(store_dir: Path | str | None = None) -> DataProfileStore:
    """Load profiles from disk, returning an empty store if the file does not exist."""

    if store_dir is None:
        store_dir = _default_store_dir()
    path = _profiles_path(store_dir)
    if not path.exists():
        return DataProfileStore()
    raw = json.loads(path.read_text(encoding="utf-8"))
    return DataProfileStore.model_validate(raw)


def profile_and_save(
    data_root: Path | str,
    store_dir: Path | str | None = None,
    extensions: tuple[str, ...] = (".csv",),
) -> DataProfileStore:
    """Scan *data_root* for structured data files, profile them, and persist.

    Returns the populated :class:`DataProfileStore`.
    """

    root = Path(data_root)
    store = DataProfileStore()

    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.name == ".gitkeep":
            continue
        ext = path.suffix.lower()
        if ext not in extensions:
            continue

        # Derive category from parent folder name
        category = path.parent.name
        if category not in ALL_CATEGORIES:
            category = "unknown"

        try:
            loaded: LoadedDataset
            loaded = load_csv(path, category)

            profile = profile_dataset(loaded)
            store.add(profile)
        except Exception as exc:  # noqa: BLE001
            error_profile = DatasetProfile(
                dataset_id=path.stem,
                category=category,
                filename=path.name,
                warnings=[f"Failed to profile: {exc}"],
                created_at="",
            )
            store.add(error_profile)

    save_profiles(store, store_dir)
    return store
