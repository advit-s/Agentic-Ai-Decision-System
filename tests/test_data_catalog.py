import json

from typer.testing import CliRunner

from decision_system.cli import app
from decision_system.data_catalog.initializer import init_data_catalog
from decision_system.data_catalog.loader import load_csv
from decision_system.data_catalog.models import ALL_CATEGORIES
from decision_system.data_catalog.profiler import profile_dataset
from decision_system.data_catalog.store import load_profiles, profile_and_save


def test_init_data_catalog_creates_manifest_and_category_folders(tmp_path):
    manifest_path = init_data_catalog(tmp_path / "company_data")

    assert manifest_path == (tmp_path / "company_data" / "manifest.json").resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert set(manifest["categories"]) == set(ALL_CATEGORIES)
    for category in ALL_CATEGORIES:
        if category == "unknown":
            continue
        assert (tmp_path / "company_data" / category / ".gitkeep").exists()


def test_profile_csv_reports_counts_missing_numeric_categorical_and_warnings(tmp_path):
    csv_path = tmp_path / "revenue.csv"
    csv_path.write_text(
        "\n".join(
            [
                "month,revenue,segment,notes",
                "2026-01,1000,enterprise,ok",
                "2026-02,1500,smb,",
                "2026-03,,enterprise,",
            ]
        ),
        encoding="utf-8",
    )

    loaded = load_csv(csv_path, "financial")
    profile = profile_dataset(loaded)
    columns = {column.name: column for column in profile.columns}

    assert profile.row_count == 3
    assert profile.column_count == 4
    assert columns["revenue"].missing_count == 1
    assert columns["revenue"].numeric_summary["min"] == 1000
    assert columns["revenue"].numeric_summary["max"] == 1500
    assert columns["segment"].top_values[0] == ("enterprise", 2)
    assert "month" in profile.detected_date_columns
    assert any("notes" in warning for warning in profile.warnings)


def test_profile_and_save_writes_profiles_under_data_profiles(tmp_path):
    data_root = tmp_path / "company_data"
    (data_root / "financial").mkdir(parents=True)
    (data_root / "financial" / "demo_revenue.csv").write_text(
        "month,revenue,segment\n2026-01,1000,enterprise\n",
        encoding="utf-8",
    )

    store = profile_and_save(data_root, tmp_path / ".decision_system")
    loaded_store = load_profiles(tmp_path / ".decision_system")
    profile_path = tmp_path / ".decision_system" / "data_profiles" / "profiles.json"

    assert profile_path.exists()
    assert store.profiles[0].filename == "demo_revenue.csv"
    assert loaded_store.profiles[0].dataset_id == "demo_revenue"


def test_cli_data_catalog_commands_exit_0(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    init_result = runner.invoke(app, ["init-data-catalog"])
    profile_result = runner.invoke(app, ["profile-data"])
    inspect_result = runner.invoke(app, ["inspect-data"])

    assert init_result.exit_code == 0
    assert "Initialized data catalog:" in init_result.output
    assert profile_result.exit_code == 0
    assert "Profiled datasets:" in profile_result.output
    assert inspect_result.exit_code == 0
    assert "# Data Catalog Inspection" in inspect_result.output
    assert (tmp_path / "company_data" / "manifest.json").exists()
    assert (tmp_path / ".decision_system" / "data_profiles" / "profiles.json").exists()
