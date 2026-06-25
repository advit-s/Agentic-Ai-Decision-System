"""Tests for the v0.3.1 synthetic demo dataset generator."""

from __future__ import annotations

import csv
from pathlib import Path

from typer.testing import CliRunner

from decision_system.cli import app
from decision_system.data_catalog.demo_data import (
    DEMO_CATEGORIES,
    seed_demo_data,
)


def _write_private(path: Path) -> None:
    """Write a non-demo CSV that should never be overwritten."""
    path.write_text("id,value\nprivate-1,999\n", encoding="utf-8")


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------


def test_seed_creates_all_demo_csv_files(tmp_path):
    """seed_demo_data creates every declared demo CSV under data_root."""
    data_root = tmp_path / "company_data"
    data_root.mkdir()
    result = seed_demo_data(data_root)
    assert result["created"] == len(DEMO_CATEGORIES)
    assert result["skipped"] == 0
    assert result["overwritten"] == 0
    for category, filename in DEMO_CATEGORIES:
        target = data_root / category / filename
        assert target.exists(), f"Missing: {target}"


def test_seed_does_not_overwrite_non_demo_files(tmp_path):
    """A private CSV that already exists is never touched; demos still create."""
    data_root = tmp_path / "company_data"
    (data_root / "financial").mkdir(parents=True)
    private_path = data_root / "financial" / "budget.csv"
    _write_private(private_path)

    result = seed_demo_data(data_root)
    assert result["created"] == len(DEMO_CATEGORIES)
    assert result["skipped"] == 0
    assert result["overwritten"] == 0
    assert private_path.exists()
    rows = _read_csv(private_path)
    assert len(rows) == 1
    assert rows[0]["id"] == "private-1"


def test_seed_overwrites_demo_files_without_force(tmp_path):
    """Without --force, existing demo files are skipped."""
    data_root = tmp_path / "company_data"
    (data_root / "financial").mkdir(parents=True)
    demo_path = data_root / "financial" / "demo_financials.csv"
    demo_path.write_text("month,revenue\n2020-01,1\n", encoding="utf-8")

    result = seed_demo_data(data_root)
    assert result["skipped"] >= 1
    assert result["overwritten"] == 0


def test_seed_force_overwrites_existing_demo_files(tmp_path):
    """--force rewrites demo files that already exist."""
    data_root = tmp_path / "company_data"
    (data_root / "financial").mkdir(parents=True)
    demo_path = data_root / "financial" / "demo_financials.csv"
    demo_path.write_text("month,revenue\n2020-01,1\n", encoding="utf-8")

    result = seed_demo_data(data_root, force=True)
    assert result["overwritten"] >= 1
    rows = _read_csv(demo_path)
    assert len(rows) >= 12  # financial has at least 12 rows
    assert rows[0]["month"] == "2025-01"


def test_generated_csvs_pass_profiler(tmp_path):
    """Every generated demo CSV is valid and can be profiled."""
    from decision_system.data_catalog.loader import load_csv
    from decision_system.data_catalog.profiler import profile_dataset

    data_root = tmp_path / "company_data"
    seed_demo_data(data_root)
    for category, filename in DEMO_CATEGORIES:
        path = data_root / category / filename
        loaded = load_csv(path, category)
        profile = profile_dataset(loaded)
        assert profile.row_count > 0
        assert profile.column_count > 0


def test_profile_data_sees_all_generated_datasets(tmp_path):
    """After seeding, profile_and_save produces a profile for each dataset."""
    from decision_system.data_catalog.store import profile_and_save

    data_root = tmp_path / "company_data"
    seed_demo_data(data_root)
    store = profile_and_save(data_root, tmp_path / ".decision_system")
    profiled_names = {p.filename for p in store.profiles}
    for _, filename in DEMO_CATEGORIES:
        assert filename in profiled_names, f"{filename} missing from profiles"


def test_no_real_data_required(tmp_path):
    """seed_demo_data works from an empty directory."""
    data_root = tmp_path / "company_data"
    data_root.mkdir()
    result = seed_demo_data(data_root)
    assert result["created"] == len(DEMO_CATEGORIES)


def test_demo_files_have_demo_prefix(tmp_path):
    """All generated files match the demo_*.csv naming convention."""
    data_root = tmp_path / "company_data"
    seed_demo_data(data_root)
    for category, filename in DEMO_CATEGORIES:
        assert filename.startswith("demo_")
        assert filename.endswith(".csv")


def test_command_exits_zero(tmp_path, monkeypatch):
    """CLI command decision-system seed-demo-data exits with code 0."""
    monkeypatch.chdir(tmp_path)
    data_root = tmp_path / "company_data"
    data_root.mkdir()
    (data_root / "financial").mkdir(parents=True)
    (data_root / "financial" / ".gitkeep").write_text("", encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(app, ["seed-demo-data"])
    assert result.exit_code == 0


def test_command_with_force_flag(tmp_path, monkeypatch):
    """CLI decision-system seed-demo-data --force exits 0 and overwrites."""
    monkeypatch.chdir(tmp_path)
    data_root = tmp_path / "company_data"
    data_root.mkdir()
    (data_root / "financial").mkdir(parents=True)
    (data_root / "financial" / ".gitkeep").write_text("", encoding="utf-8")
    demo = data_root / "financial" / "demo_financials.csv"
    demo.write_text("month,revenue\n2020-01,1\n", encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(app, ["seed-demo-data", "--force"])
    assert result.exit_code == 0
    rows = _read_csv(demo)
    assert len(rows) >= 12
