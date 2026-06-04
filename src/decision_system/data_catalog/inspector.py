"""Inspection helpers for data catalog profiles."""

from __future__ import annotations

from decision_system.data_catalog.models import DataProfileStore


def inspect_profiles(store: DataProfileStore) -> dict[str, int | dict[str, int]]:
    """Compute summary statistics from a profile store.

    Returns a dict with:
      - total_datasets
      - total_rows
      - datasets_by_category  (category -> count)
      - rows_by_category      (category -> total row count)
      - warning_counts        (level -> count)
      - datasets_with_warnings
    """

    by_cat_count: dict[str, int] = {}
    by_cat_rows: dict[str, int] = {}
    total_rows = 0
    warn_datasets = 0

    for p in store.profiles:
        by_cat_count[p.category] = by_cat_count.get(p.category, 0) + 1
        by_cat_rows[p.category] = by_cat_rows.get(p.category, 0) + p.row_count
        total_rows += p.row_count
        if p.warnings:
            warn_datasets += 1

    return {
        "total_datasets": len(store.profiles),
        "total_rows": total_rows,
        "datasets_by_category": by_cat_count,
        "rows_by_category": by_cat_rows,
        "total_warnings": store.total_warnings(),
        "datasets_with_warnings": warn_datasets,
    }


def render_inspection(summary: dict[str, int | dict[str, int]]) -> str:
    """Render the inspection summary as a human-readable string."""

    lines: list[str] = ["# Data Catalog Inspection", ""]

    lines.append(f"Total datasets: {summary['total_datasets']}")
    lines.append(f"Total rows: {summary['total_rows']}")
    lines.append(f"Total warnings: {summary['total_warnings']}")
    lines.append("")
    lines.append("## Datasets by Category")
    lines.append("")

    categories: dict[str, int] = summary["datasets_by_category"]
    rows_by_cat: dict[str, int] = summary["rows_by_category"]
    for cat in sorted(categories):
        lines.append(f"- **{cat}**: {categories[cat]} dataset(s), {rows_by_cat.get(cat, 0)} rows")

    lines.append("")
    return "\n".join(lines)
