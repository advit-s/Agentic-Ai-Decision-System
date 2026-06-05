"""Offline tests for public dataset importing."""

from __future__ import annotations

import csv
import zipfile
from pathlib import Path

from typer.testing import CliRunner

from decision_system.cli import app
from decision_system.data_catalog.importer import (
    classify_dataset,
    import_datasets,
    load_import_manifest,
)


def _write_csv(path: Path) -> None:
    path.write_text("name,value\nA,1\nB,2\nC,3\n", encoding="utf-8")


def _write_minimal_xlsx(path: Path) -> None:
    sheet_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData>
    <row r="1"><c r="A1" t="inlineStr"><is><t>name</t></is></c><c r="B1" t="inlineStr"><is><t>value</t></is></c></row>
    <row r="2"><c r="A2" t="inlineStr"><is><t>A</t></is></c><c r="B2"><v>1</v></c></row>
    <row r="3"><c r="A3" t="inlineStr"><is><t>B</t></is></c><c r="B3"><v>2</v></c></row>
  </sheetData>
</worksheet>"""
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("xl/worksheets/sheet1.xml", sheet_xml)


def test_classifier_maps_known_public_dataset_names():
    assert classify_dataset("Online Retail.xlsx") == "sales"
    assert classify_dataset("sample_-_superstore.xls") == "sales"
    assert classify_dataset("Data Set- Inc5000 Company List_2014.csv") == "competitors"
    assert classify_dataset("EMSI_JobChange_UK.xlsx") == "operations"
    assert classify_dataset("EMSI_MillenialsvsBabyBoomers.xls") == "strategic"


def test_importer_imports_csv_and_saves_manifest(tmp_path):
    source_dir = tmp_path / "datasets"
    data_root = tmp_path / "company_data"
    manifest_path = tmp_path / ".decision_system" / "imports" / "import_manifest.json"
    source_dir.mkdir()
    _write_csv(source_dir / "Data Set- Inc5000 Company List_2014.csv")

    manifest = import_datasets(source_dir, data_root=data_root, manifest_path=manifest_path)

    assert manifest.imported_count == 1
    output = data_root / "competitors" / "imported_data_set_inc5000_company_list_2014.csv"
    assert output.exists()
    assert load_import_manifest(manifest_path).imported_count == 1


def test_importer_imports_xlsx_and_limits_rows(tmp_path):
    source_dir = tmp_path / "datasets"
    data_root = tmp_path / "company_data"
    source_dir.mkdir()
    _write_minimal_xlsx(source_dir / "Online Retail.xlsx")

    manifest = import_datasets(source_dir, data_root=data_root, max_rows=1)

    output = data_root / "sales" / "imported_online_retail.csv"
    with output.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    assert manifest.imported_count == 1
    assert len(rows) == 1


def test_importer_skips_bak_with_clear_reason(tmp_path):
    source_dir = tmp_path / "datasets"
    source_dir.mkdir()
    (source_dir / "AdventureWorks2022.bak").write_bytes(b"not imported")

    manifest = import_datasets(source_dir, data_root=tmp_path / "company_data")

    assert manifest.imported_count == 0
    assert manifest.skipped_count == 1
    assert "SQL Server .bak files are not imported" in manifest.records[0].reason


def test_importer_dry_run_writes_nothing(tmp_path):
    source_dir = tmp_path / "datasets"
    data_root = tmp_path / "company_data"
    manifest_path = tmp_path / ".decision_system" / "imports" / "import_manifest.json"
    source_dir.mkdir()
    _write_csv(source_dir / "Data Set- Inc5000 Company List_2014.csv")

    manifest = import_datasets(
        source_dir,
        data_root=data_root,
        manifest_path=manifest_path,
        dry_run=True,
    )

    assert manifest.imported_count == 1
    assert not data_root.exists()
    assert not manifest_path.exists()


def test_importer_force_controls_overwrites(tmp_path):
    source_dir = tmp_path / "datasets"
    data_root = tmp_path / "company_data"
    source_dir.mkdir()
    _write_csv(source_dir / "Online Retail.csv")
    output = data_root / "sales" / "imported_online_retail.csv"
    output.parent.mkdir(parents=True)
    output.write_text("old,value\nold,old\n", encoding="utf-8")

    skipped = import_datasets(source_dir, data_root=data_root)
    overwritten = import_datasets(source_dir, data_root=data_root, force=True)

    assert skipped.imported_count == 0
    assert skipped.skipped_count == 1
    assert overwritten.imported_count == 1
    assert output.read_text(encoding="utf-8").startswith("name,value")


def test_cli_import_and_inspect_commands_exit_zero(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    source_dir = tmp_path / "datasets"
    source_dir.mkdir()
    _write_csv(source_dir / "Online Retail.csv")
    runner = CliRunner()

    import_result = runner.invoke(app, ["import-datasets", "--source-dir", str(source_dir), "--max-rows", "2"])
    inspect_result = runner.invoke(app, ["inspect-imports"])

    assert import_result.exit_code == 0
    # Strip ANSI color codes for assertion
    output_no_ansi = import_result.output.replace("\x1b[1;36m", "").replace("\x1b[0m", "").replace("\x1b[1m", "")
    assert "Imported datasets: 1" in output_no_ansi
    assert inspect_result.exit_code == 0
    assert "# Dataset Import Inspection" in inspect_result.output
