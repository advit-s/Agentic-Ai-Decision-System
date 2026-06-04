"""Load local CSV files for profiling."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from decision_system.data_catalog.models import DataCategory, dataset_id_from_filename


class LoadedDataset:
    """Raw rows and header from a structured data file."""

    def __init__(
        self,
        dataset_id: str,
        category: DataCategory,
        filename: Path,
        headers: list[str],
        rows: list[dict[str, Any]],
        warnings: list[str] | None = None,
    ) -> None:
        self.dataset_id = dataset_id
        self.category = category
        self.filename = filename
        self.headers = headers
        self.rows = rows
        self.warnings: list[str] = warnings or []

    @property
    def row_count(self) -> int:
        return len(self.rows)

    @property
    def column_count(self) -> int:
        return len(self.headers)


# -------------------------------------------------------------------
# CSV loader
# -------------------------------------------------------------------

def load_csv(path: Path, category: DataCategory) -> LoadedDataset:
    """Read a CSV file and return a :class:`LoadedDataset`."""

    dataset_id = dataset_id_from_filename(path.name)
    warnings: list[str] = []

    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        headers = list(reader.fieldnames or [])
        rows: list[dict[str, Any]] = []
        for line_no, row in enumerate(reader, start=2):
            rows.append(dict(row))
            if len(row) != len(headers):
                warnings.append(
                    f"Row {line_no}: field count ({len(row)}) does not match header ({len(headers)})"
                )

    if not headers:
        warnings.append("File has no header row or is empty")

    return LoadedDataset(
        dataset_id=dataset_id,
        category=category,
        filename=path,
        headers=headers,
        rows=rows,
        warnings=warnings,
    )

