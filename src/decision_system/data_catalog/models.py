"""Pydantic models for the local data catalog profiling subsystem."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------

DataCategory = Literal[
    "financial",
    "customers",
    "sales",
    "marketing",
    "feedback",
    "products",
    "competitors",
    "operations",
    "analytics",
    "strategic",
    "unknown",
]

CATEGORY_DESCRIPTIONS: dict[str, str] = {
    "financial": "Revenue, expenses, margins, and budget data",
    "customers": "Customer demographics, segments, and lifetime value",
    "sales": "Sales transactions, pipelines, and lead sources",
    "marketing": "Campaigns, channels, and marketing metrics",
    "feedback": "Customer surveys, reviews, and support tickets",
    "products": "Product catalog, features, and usage data",
    "competitors": "Competitor intelligence and market positioning",
    "operations": "Operational KPIs, logistics, and process data",
    "analytics": "Website/app analytics, events, and engagement",
    "strategic": "Board decks, OKRs, and strategic plans",
    "unknown": "Data that does not fit any known category",
}

ALL_CATEGORIES: list[str] = list(CATEGORY_DESCRIPTIONS.keys())


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------


class ColumnProfile(BaseModel):
    """Profile summary for a single column."""

    name: str
    dtype: str = ""
    missing_count: int = 0
    missing_pct: float = 0.0
    unique_count: int = 0
    numeric_summary: dict[str, float] = Field(default_factory=dict)
    top_values: list[tuple[str, int]] = Field(default_factory=list)


class DatasetProfile(BaseModel):
    """Full profile of one CSV dataset."""

    dataset_id: str
    category: DataCategory
    filename: str
    row_count: int = 0
    column_count: int = 0
    columns: list[ColumnProfile] = Field(default_factory=list)
    detected_date_columns: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    created_at: str = ""


# ---------------------------------------------------------------------------
# Manifest / store
# ---------------------------------------------------------------------------


class DataSourceManifest(BaseModel):
    """Registry describing supported data categories."""

    version: str = "0.3"
    categories: dict[str, str] = Field(default_factory=lambda: dict(CATEGORY_DESCRIPTIONS))
    allowed_file_types: list[str] = Field(default_factory=lambda: [".csv"])
    demo_datasets: list[dict[str, str | bool]] = Field(default_factory=list)


class DataProfileStore(BaseModel):
    """In-memory container for all dataset profiles."""

    profiles: list[DatasetProfile] = Field(default_factory=list)

    # -- convenience helpers --------------------------------------------------

    def add(self, profile: DatasetProfile) -> None:
        """Append a profile, replacing any existing one with the same id."""

        self.profiles = [p for p in self.profiles if p.dataset_id != profile.dataset_id]
        self.profiles.append(profile)

    def get_by_dataset_id(self, dataset_id: str) -> DatasetProfile | None:
        for p in self.profiles:
            if p.dataset_id == dataset_id:
                return p
        return None

    def group_by_category(self) -> dict[str, list[DatasetProfile]]:
        groups: dict[str, list[DatasetProfile]] = {}
        for p in self.profiles:
            groups.setdefault(p.category, []).append(p)
        return groups

    def total_warnings(self) -> int:
        return sum(len(p.warnings) for p in self.profiles)


def dataset_id_from_filename(filename: str) -> str:
    """Derive a stable dataset ID from a file name."""

    return Path(filename).stem
