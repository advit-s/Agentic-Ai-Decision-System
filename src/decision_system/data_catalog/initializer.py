"""Create the local `company_data/` folder structure and manifest."""

from __future__ import annotations

import json
from pathlib import Path

from decision_system.data_catalog.models import (
    ALL_CATEGORIES,
    DataCategory,
    DataSourceManifest,
    dataset_id_from_filename,
)


DEFAULT_DATA_ROOT = Path("company_data")
MANIFEST_FILENAME = "manifest.json"

DEMO_DATASETS: tuple[dict[str, str], ...] = (
    {
        "category": "financial",
        "filename": "demo_revenue.csv",
        "description": "Fake monthly revenue sample for local profiling smoke tests.",
        "content": "\n".join(
            [
                "month,revenue,segment,notes",
                "2026-01,1000,enterprise,baseline fake row",
                "2026-02,1500,smb,",
                "2026-03,,enterprise,missing value demo",
            ]
        )
        + "\n",
    },
    {
        "category": "customers",
        "filename": "demo_customers.csv",
        "description": "Fake customer segment sample for local profiling smoke tests.",
        "content": "\n".join(
            [
                "customer_id,segment,lifetime_value,risk_flag",
                "demo-cust-001,enterprise,12000,false",
                "demo-cust-002,smb,4500,true",
                "demo-cust-003,enterprise,9800,false",
            ]
        )
        + "\n",
    },
)


def dataset_id(filename: str) -> str:
    """Derive a stable dataset ID from a filename."""

    return dataset_id_from_filename(filename)


def category_for_filename(filename: str) -> DataCategory:
    """Return the category that matches the parent folder name."""

    parent = Path(filename).parent.name
    if parent in ALL_CATEGORIES:
        return parent  # type: ignore[return-value]
    return "unknown"


def init_data_catalog(data_root: Path | str = DEFAULT_DATA_ROOT) -> Path:
    """Create the folder tree, fake demo CSVs, and manifest."""

    root = Path(data_root)
    manifest_path = root / MANIFEST_FILENAME

    for category in ALL_CATEGORIES:
        if category == "unknown":
            continue
        folder = root / category
        folder.mkdir(parents=True, exist_ok=True)
        gitkeep = folder / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.write_text("", encoding="utf-8")

    demo_entries: list[dict[str, str | bool]] = []
    for demo in DEMO_DATASETS:
        category = demo["category"]
        filename = demo["filename"]
        relative_path = f"{category}/{filename}"
        demo_path = root / relative_path
        if not demo_path.exists():
            demo_path.write_text(demo["content"], encoding="utf-8")
        demo_entries.append(
            {
                "dataset_id": dataset_id(filename),
                "category": category,
                "filename": filename,
                "relative_path": relative_path,
                "file_type": ".csv",
                "description": demo["description"],
                "is_demo": True,
            }
        )

    manifest = DataSourceManifest(demo_datasets=demo_entries)
    manifest_path.write_text(
        json.dumps(manifest.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )

    return manifest_path.resolve()
