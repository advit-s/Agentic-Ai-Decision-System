"""Profile a loaded CSV dataset and produce a `DatasetProfile`."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from statistics import mean, median, stdev

from decision_system.data_catalog.loader import LoadedDataset
from decision_system.data_catalog.models import ColumnProfile, DatasetProfile

_DATE_RE = re.compile(r"date|time|month|year|day|period|week", re.IGNORECASE)
_NUMERIC_RE = re.compile(
    r"amount|revenue|cost|price|margin|value|count|\$",
    re.IGNORECASE,
)
_NUMERIC_RE2 = re.compile(r"profit|sales|customers|lifetime|total", re.IGNORECASE)


def _looks_numeric(header: str) -> bool:
    return bool(_NUMERIC_RE.search(header) or _NUMERIC_RE2.search(header))


def _looks_date(header: str) -> bool:
    return bool(_DATE_RE.search(header))


def _safe_float(values: list[str]) -> list[float]:
    nums: list[float] = []
    for value in values:
        cleaned = value.strip().replace(",", "").replace("$", "").replace("%", "")
        if not cleaned:
            continue
        try:
            nums.append(float(cleaned))
        except ValueError:
            pass
    return nums


def _numeric_stats(values: list[float]) -> dict[str, float]:
    if not values:
        return {}
    if len(values) == 1:
        value = values[0]
        return {"min": value, "max": value, "mean": value, "median": value}
    return {
        "min": min(values),
        "max": max(values),
        "mean": round(mean(values), 4),
        "median": round(median(values), 4),
        "std": round(stdev(values), 4),
    }


def profile_dataset(dataset: LoadedDataset) -> DatasetProfile:
    """Build a profile from a loaded CSV dataset."""

    warnings = list(dataset.warnings)
    columns: list[ColumnProfile] = []
    detected_date_columns: list[str] = []
    total_rows = dataset.row_count

    for header in dataset.headers:
        col_values = [row.get(header, "") for row in dataset.rows]
        non_empty = [value for value in col_values if value.strip()]
        missing = total_rows - len(non_empty)
        missing_pct = round(missing / total_rows, 4) if total_rows else 0.0
        unique_count = len(set(col_values))

        numeric_summary: dict[str, float] = {}
        top_values: list[tuple[str, int]] = []

        if non_empty:
            nums = _safe_float(non_empty)
            if nums and (_looks_numeric(header) or len(nums) == len(non_empty)):
                numeric_summary = _numeric_stats(nums)

            if not numeric_summary:
                frequencies: dict[str, int] = {}
                for value in non_empty:
                    frequencies[value] = frequencies.get(value, 0) + 1
                top_values = sorted(
                    frequencies.items(),
                    key=lambda item: (-item[1], item[0]),
                )[:10]

        columns.append(
            ColumnProfile(
                name=header,
                dtype="numeric" if numeric_summary else "categorical",
                missing_count=missing,
                missing_pct=missing_pct,
                unique_count=unique_count,
                numeric_summary=numeric_summary,
                top_values=top_values,
            )
        )

        if _looks_date(header) and not numeric_summary:
            detected_date_columns.append(header)

    if total_rows == 0:
        warnings.append("Dataset has no data rows")
    for column in columns:
        if column.missing_pct > 0.5:
            warnings.append(f"Column '{column.name}' is >50% missing ({column.missing_pct:.0%})")

    return DatasetProfile(
        dataset_id=dataset.dataset_id,
        category=dataset.category,
        filename=dataset.filename.name,
        row_count=total_rows,
        column_count=dataset.column_count,
        columns=columns,
        detected_date_columns=detected_date_columns,
        warnings=warnings,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
