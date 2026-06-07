"""Tests for the v0.9 local web UI prototype."""

from __future__ import annotations

import importlib
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = ROOT / "web"
MOCK_DIR = WEB_DIR / "mock-data"


REQUIRED_STATIC_FILES = [
    WEB_DIR / "index.html",
    WEB_DIR / "app.js",
    WEB_DIR / "styles.css",
]

REQUIRED_MOCK_FILES = [
    MOCK_DIR / "report.json",
    MOCK_DIR / "insights.json",
    MOCK_DIR / "ontology.json",
    MOCK_DIR / "war-room.json",
    MOCK_DIR / "provider-evals.json",
    MOCK_DIR / "data-profiles.json",
    MOCK_DIR / "graph.json",
]


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_static_web_ui_files_exist():
    for path in REQUIRED_STATIC_FILES:
        assert path.exists(), f"Missing web UI static file: {path}"
        assert path.stat().st_size > 0


def test_index_references_sections_and_mock_first_runtime():
    html = (WEB_DIR / "index.html").read_text(encoding="utf-8")
    script = (WEB_DIR / "app.js").read_text(encoding="utf-8")

    for section_id in (
        "ask",
        "reports",
        "insights",
        "ontology",
        "war-room",
        "provider-evals",
        "data-profiles",
        "graph",
    ):
        assert f'id="{section_id}"' in html

    assert "apiBaseUrl" in html
    assert "mock-data/" in script
    assert "localStorage" in script


def test_mock_data_files_are_valid_lightweight_json():
    for path in REQUIRED_MOCK_FILES:
        payload = _load_json(path)
        assert isinstance(payload, dict), f"{path.name} should contain one JSON object"
        assert path.stat().st_size < 25_000, f"{path.name} should not contain raw datasets"


def test_mock_data_contracts_cover_required_views():
    report = _load_json(MOCK_DIR / "report.json")
    insights = _load_json(MOCK_DIR / "insights.json")
    ontology = _load_json(MOCK_DIR / "ontology.json")
    war_room = _load_json(MOCK_DIR / "war-room.json")
    provider_evals = _load_json(MOCK_DIR / "provider-evals.json")
    data_profiles = _load_json(MOCK_DIR / "data-profiles.json")
    graph = _load_json(MOCK_DIR / "graph.json")

    assert report["question"]
    assert report["markdown"].startswith("#")
    assert len(insights["insights"]) >= 3
    assert {"severity", "category", "title", "summary"} <= set(insights["insights"][0])
    assert len(ontology["mappings"]) >= 3
    assert {"dataset", "column", "concept_id", "concept_name"} <= set(ontology["mappings"][0])
    assert len(war_room["roles"]) >= 2
    assert len(war_room["artifacts"]) >= 2
    assert "judge_interventions" in war_room
    assert provider_evals["provider_name"] == "fake"
    assert len(provider_evals["results"]) >= 1
    assert len(data_profiles["profiles"]) >= 2
    assert {"dataset", "row_count", "columns"} <= set(data_profiles["profiles"][0])
    assert len(graph["entities"]) >= 2
    assert len(graph["relationships"]) >= 1


def test_package_relative_web_dir_exists():
    """Package-relative web assets should exist for pip-installed environments."""
    import decision_system

    pkg_dir = Path(decision_system.__file__).parent
    web_dir = pkg_dir / "web"
    assert web_dir.exists(), f"Package web directory missing: {web_dir}"
    assert (web_dir / "index.html").exists()
    assert (web_dir / "app.js").exists()
    assert (web_dir / "styles.css").exists()


def test_fastapi_ui_route_returns_page_if_api_module_exists():
    spec = importlib.util.find_spec("decision_system.api")
    if spec is None:
        pytest.skip("No FastAPI API package exists in this branch.")

    testclient = pytest.importorskip("fastapi.testclient")
    api_module = importlib.import_module("decision_system.api")

    app = getattr(api_module, "app", None)
    if app is None and hasattr(api_module, "create_app"):
        app = api_module.create_app()
    if app is None:
        pytest.skip("decision_system.api exists but exposes no app/create_app.")

    client = testclient.TestClient(app)
    response = client.get("/")

    assert response.status_code == 200
    assert "Local Web UI Prototype" in response.text or "decision" in response.text.lower()

# v0.9.2: root and package web assets must stay byte-for-byte identical.
_SYNCED_FILES = [
    "index.html",
    "app.js",
    "styles.css",
]

_MOCK_SUBDIR = "mock-data"


def _web_paths():
    root = Path(__file__).resolve().parents[1]
    return root / "web", root / "src" / "decision_system" / "web"


def test_root_and_package_web_assets_match():
    root_web, pkg_web = _web_paths()
    for name in _SYNCED_FILES:
        root_file = root_web / name
        pkg_file = pkg_web / name
        assert root_file.exists(), f"Missing root web file: {root_file}"
        assert pkg_file.exists(), f"Missing package web file: {pkg_file}"
        assert root_file.read_bytes() == pkg_file.read_bytes(), (
            f"Web asset drift detected: {name} differs between root and package."
        )


def test_root_and_package_mock_data_match():
    root_web, pkg_web = _web_paths()
    root_mock = root_web / _MOCK_SUBDIR
    pkg_mock = pkg_web / _MOCK_SUBDIR
    assert root_mock.exists() and pkg_mock.exists()
    root_files = sorted(p.name for p in root_mock.iterdir() if p.is_file())
    pkg_files = sorted(p.name for p in pkg_mock.iterdir() if p.is_file())
    assert root_files == pkg_files
    for name in root_files:
        assert (root_mock / name).read_bytes() == (pkg_mock / name).read_bytes(), (
            f"Mock data drift detected: {name} differs between root and package."
        )
