"""Local public dataset importer for CSV and spreadsheet files.

The importer converts user-provided public datasets from an ignored
``datasets/`` folder into categorized CSV files under ``company_data/``.
It does not import SQL Server backups, call connectors, or use a database.
"""

from __future__ import annotations

import csv
import re
import zipfile
from datetime import datetime, timezone
from html import unescape
from importlib import import_module
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from pydantic import BaseModel, Field

from decision_system._data_root import get_data_root
from decision_system.data_catalog.models import DataCategory

DEFAULT_IMPORT_SOURCE_DIR = Path("datasets")


def _default_import_manifest_path() -> Path:
    return get_data_root() / "imports" / "import_manifest.json"


class ImportRecord(BaseModel):
    """One source dataset import or skip event."""

    source_filename: str
    source_path: str
    status: str
    category: DataCategory = "unknown"
    output_path: str = ""
    output_filename: str = ""
    row_count: int = 0
    reason: str = ""


class ImportManifest(BaseModel):
    """Auditable result of a dataset import run."""

    created_at: str
    source_dir: str
    dry_run: bool = False
    max_rows: int
    records: list[ImportRecord] = Field(default_factory=list)

    @property
    def imported_count(self) -> int:
        return sum(1 for record in self.records if record.status == "imported")

    @property
    def skipped_count(self) -> int:
        return sum(1 for record in self.records if record.status == "skipped")


def import_datasets(
    source_dir: Path | str = DEFAULT_IMPORT_SOURCE_DIR,
    *,
    data_root: Path | str = Path("company_data"),
    manifest_path: Path | str | None = None,
    max_rows: int = 5000,
    force: bool = False,
    dry_run: bool = False,
) -> ImportManifest:
    """Import supported local public datasets into categorized CSV files."""

    if manifest_path is None:
        manifest_path = _default_import_manifest_path()
    source_root = Path(source_dir)
    manifest = ImportManifest(
        created_at=datetime.now(timezone.utc).isoformat(),
        source_dir=str(source_root),
        dry_run=dry_run,
        max_rows=max_rows,
    )

    if not source_root.exists():
        manifest.records.append(
            ImportRecord(
                source_filename="",
                source_path=str(source_root),
                status="skipped",
                reason="Source directory does not exist",
            )
        )
        _save_import_manifest(manifest, manifest_path, dry_run=dry_run)
        return manifest

    for path in sorted(source_root.iterdir(), key=lambda item: item.name.lower()):
        if path.is_dir():
            continue
        ext = path.suffix.lower()
        category = classify_dataset(path.name)
        if ext == ".bak":
            manifest.records.append(
                _skipped(
                    path,
                    category,
                    "SQL Server .bak files are not imported; export tables to CSV first",
                )
            )
            continue
        if ext not in {".csv", ".xlsx", ".xls"}:
            manifest.records.append(
                _skipped(path, category, f"Unsupported file type: {ext or '(none)'}")
            )
            continue

        output_filename = f"imported_{_slug(path.stem)}.csv"
        output_path = Path(data_root) / category / output_filename
        if output_path.exists() and not force:
            manifest.records.append(
                ImportRecord(
                    source_filename=path.name,
                    source_path=str(path),
                    status="skipped",
                    category=category,
                    output_path=str(output_path),
                    output_filename=output_filename,
                    reason="Output already exists; pass --force to overwrite",
                )
            )
            continue

        try:
            headers, rows = _read_source_rows(path, max_rows=max_rows)
        except Exception as exc:  # noqa: BLE001
            manifest.records.append(_skipped(path, category, f"Failed to read dataset: {exc}"))
            continue

        if not headers:
            manifest.records.append(_skipped(path, category, "No header row found"))
            continue

        if not dry_run:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            _write_csv(output_path, headers, rows)
        manifest.records.append(
            ImportRecord(
                source_filename=path.name,
                source_path=str(path),
                status="imported",
                category=category,
                output_path=str(output_path),
                output_filename=output_filename,
                row_count=len(rows),
            )
        )

    _save_import_manifest(manifest, manifest_path, dry_run=dry_run)
    return manifest


def load_import_manifest(
    manifest_path: Path | str | None = None,
) -> ImportManifest:
    """Load the latest import manifest or return an empty manifest."""

    if manifest_path is None:
        manifest_path = _default_import_manifest_path()
    path = Path(manifest_path)
    if not path.exists():
        return ImportManifest(
            created_at="",
            source_dir="",
            max_rows=0,
        )
    return ImportManifest.model_validate_json(path.read_text(encoding="utf-8"))


def render_import_manifest(manifest: ImportManifest) -> str:
    """Render import results for CLI inspection."""

    lines = [
        "# Dataset Import Inspection",
        "",
        f"Source directory: {manifest.source_dir or '(none)'}",
        f"Imported count: {manifest.imported_count}",
        f"Skipped count: {manifest.skipped_count}",
        "",
        "## Records",
        "",
    ]
    if not manifest.records:
        lines.append("- (none)")
        return "\n".join(lines)
    for record in manifest.records:
        detail = record.output_path if record.status == "imported" else record.reason
        lines.append(
            f"- {record.source_filename or record.source_path}: {record.status} "
            f"({record.category}, rows={record.row_count}) {detail}"
        )
    return "\n".join(lines)


def classify_dataset(filename: str) -> DataCategory:
    """Classify known public dataset filenames into v0.3 categories."""

    normalized = filename.lower()
    if "online retail" in normalized or "superstore" in normalized:
        return "sales"
    if "inc5000" in normalized or "inc5000" in normalized.replace(" ", ""):
        return "competitors"
    if "jobchange" in normalized or "job change" in normalized:
        return "operations"
    if "millenial" in normalized or "millennial" in normalized or "babyboomer" in normalized:
        return "strategic"
    return "unknown"


def _read_source_rows(path: Path, *, max_rows: int) -> tuple[list[str], list[dict[str, str]]]:
    ext = path.suffix.lower()
    if ext == ".csv":
        return _read_csv(path, max_rows=max_rows)
    if ext == ".xlsx":
        return _read_xlsx(path, max_rows=max_rows)
    if ext == ".xls":
        return _read_xls(path, max_rows=max_rows)
    raise ValueError(f"Unsupported file type: {ext}")


def _read_csv(path: Path, *, max_rows: int) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        headers = [header or "" for header in (reader.fieldnames or [])]
        rows = [_clean_row(row, headers) for _, row in zip(range(max_rows), reader)]
    return headers, rows


def _read_xlsx(path: Path, *, max_rows: int) -> tuple[list[str], list[dict[str, str]]]:
    with zipfile.ZipFile(path) as archive:
        shared_strings = _xlsx_shared_strings(archive)
        sheet_names = sorted(
            name
            for name in archive.namelist()
            if name.startswith("xl/worksheets/sheet") and name.endswith(".xml")
        )
        if not sheet_names:
            raise ValueError("Workbook has no worksheet XML")
        rows = _xlsx_sheet_rows(archive.read(sheet_names[0]), shared_strings)
    return _table_from_rows(rows, max_rows=max_rows)


def _read_xls(path: Path, *, max_rows: int) -> tuple[list[str], list[dict[str, str]]]:
    try:
        xlrd = import_module("xlrd")
    except ModuleNotFoundError as exc:
        raise ValueError("XLS import requires optional dependency xlrd") from exc

    workbook = xlrd.open_workbook(str(path))
    sheet = workbook.sheet_by_index(0)
    raw_rows: list[list[str]] = []
    for row_index in range(min(sheet.nrows, max_rows + 1)):
        raw_rows.append(
            [
                str(sheet.cell_value(row_index, col_index)).strip()
                for col_index in range(sheet.ncols)
            ]
        )
    return _table_from_rows(raw_rows, max_rows=max_rows)


def _xlsx_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    try:
        payload = archive.read("xl/sharedStrings.xml")
    except KeyError:
        return []
    root = ElementTree.fromstring(payload)
    strings: list[str] = []
    for item in root.iter():
        if item.tag.endswith("}si"):
            parts = [node.text or "" for node in item.iter() if node.tag.endswith("}t")]
            strings.append(unescape("".join(parts)))
    return strings


def _xlsx_sheet_rows(payload: bytes, shared_strings: list[str]) -> list[list[str]]:
    root = ElementTree.fromstring(payload)
    rows: list[list[str]] = []
    for row in root.iter():
        if not row.tag.endswith("}row"):
            continue
        values: list[str] = []
        for cell in row:
            if not cell.tag.endswith("}c"):
                continue
            cell_type = cell.attrib.get("t", "")
            raw_value = ""
            for node in cell:
                if node.tag.endswith("}v") or node.tag.endswith("}t"):
                    raw_value = node.text or ""
                    break
                if node.tag.endswith("}is"):
                    raw_value = "".join(
                        text.text or "" for text in node.iter() if text.tag.endswith("}t")
                    )
                    break
            if cell_type == "s" and raw_value:
                raw_value = shared_strings[int(raw_value)]
            values.append(raw_value.strip())
        rows.append(values)
    return rows


def _table_from_rows(
    raw_rows: list[list[str]], *, max_rows: int
) -> tuple[list[str], list[dict[str, str]]]:
    if not raw_rows:
        return [], []
    headers = [_header(value, index) for index, value in enumerate(raw_rows[0])]
    rows = [
        {
            headers[index]: row[index].strip() if index < len(row) else ""
            for index in range(len(headers))
        }
        for row in raw_rows[1 : max_rows + 1]
    ]
    return headers, rows


def _write_csv(path: Path, headers: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def _save_import_manifest(
    manifest: ImportManifest,
    manifest_path: Path | str,
    *,
    dry_run: bool,
) -> None:
    if dry_run:
        return
    path = Path(manifest_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(manifest.model_dump_json(indent=2) + "\n", encoding="utf-8")


def _clean_row(row: dict[str, Any], headers: list[str]) -> dict[str, str]:
    return {header: str(row.get(header, "") or "").strip() for header in headers}


def _header(value: str, index: int) -> str:
    cleaned = re.sub(r"\s+", "_", str(value).strip().lower())
    cleaned = re.sub(r"[^a-z0-9_]+", "", cleaned).strip("_")
    return cleaned or f"column_{index + 1}"


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "dataset"


def _skipped(path: Path, category: DataCategory, reason: str) -> ImportRecord:
    return ImportRecord(
        source_filename=path.name,
        source_path=str(path),
        status="skipped",
        category=category,
        reason=reason,
    )
