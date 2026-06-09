"""Tests for the v1.7 product web UI."""

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
    MOCK_DIR / "dashboard.json",
    MOCK_DIR / "report.json",
    MOCK_DIR / "insights.json",
    MOCK_DIR / "ontology.json",
    MOCK_DIR / "war-room.json",
    MOCK_DIR / "provider-evals.json",
    MOCK_DIR / "data-profiles.json",
    MOCK_DIR / "graph.json",
    MOCK_DIR / "security.json",
    MOCK_DIR / "connectors.json",
    MOCK_DIR / "observability.json",
    MOCK_DIR / "enterprise-readiness.json",
]


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_static_web_ui_files_exist():
    for path in REQUIRED_STATIC_FILES:
        assert path.exists(), f"Missing web UI static file: {path}"
        assert path.stat().st_size > 0


def test_index_references_all_product_sections():
    html = (WEB_DIR / "index.html").read_text(encoding="utf-8")
    script = (WEB_DIR / "app.js").read_text(encoding="utf-8")

    for section_id in (
        "dashboard",
        "ask",
        "data",
        "war-room",
        "workspaces",
        "connectors",
        "security",
        "observability",
        "enterprise",
    ):
        assert f'id="{section_id}"' in html, f"Missing section id={section_id} in index.html"

    assert "apiBaseUrl" in html
    assert "mock-data/" in script
    assert "localStorage" in script


def test_mock_data_files_are_valid_lightweight_json():
    for path in REQUIRED_MOCK_FILES:
        payload = _load_json(path)
        assert isinstance(payload, dict), f"{path.name} should contain one JSON object"
        assert path.stat().st_size < 50_000, f"{path.name} should not contain raw datasets"


def test_mock_data_contracts_cover_required_views():
    dashboard = _load_json(MOCK_DIR / "dashboard.json")
    report = _load_json(MOCK_DIR / "report.json")
    insights = _load_json(MOCK_DIR / "insights.json")
    ontology = _load_json(MOCK_DIR / "ontology.json")
    war_room = _load_json(MOCK_DIR / "war-room.json")
    provider_evals = _load_json(MOCK_DIR / "provider-evals.json")
    data_profiles = _load_json(MOCK_DIR / "data-profiles.json")
    graph = _load_json(MOCK_DIR / "graph.json")
    security = _load_json(MOCK_DIR / "security.json")
    connectors = _load_json(MOCK_DIR / "connectors.json")
    observability = _load_json(MOCK_DIR / "observability.json")
    enterprise = _load_json(MOCK_DIR / "enterprise-readiness.json")

    # Dashboard contract
    assert "version" in dashboard
    assert "system_ready" in dashboard

    # Report contract
    assert report["question"]
    assert report["markdown"].startswith("#")

    # Insights contract
    assert len(insights["insights"]) >= 3
    assert {"severity", "category", "title", "summary"} <= set(insights["insights"][0])

    # Ontology contract
    assert len(ontology["mappings"]) >= 3
    assert {"dataset", "column", "concept_id", "concept_name"} <= set(ontology["mappings"][0])

    # War room contract
    assert len(war_room["roles"]) >= 2
    assert len(war_room["artifacts"]) >= 2
    assert "judge_interventions" in war_room

    # Provider evals contract
    assert provider_evals["provider_name"] == "fake"
    assert len(provider_evals["results"]) >= 1

    # Data profiles contract
    assert len(data_profiles["profiles"]) >= 2
    assert {"dataset", "row_count", "columns"} <= set(data_profiles["profiles"][0])

    # Graph contract
    assert len(graph["entities"]) >= 2
    assert len(graph["relationships"]) >= 1

    # Security contract
    assert "policy" in security
    assert "audit_events" in security
    assert "approval_requests" in security

    # Connectors contract
    assert len(connectors["connectors"]) >= 4
    assert "jobs" in connectors

    # Observability contract
    assert "metrics" in observability
    assert "eval_runs" in observability

    # Enterprise readiness contract
    assert enterprise["readiness_level"] == "prototype-ready"
    assert enterprise["passed_count"] >= 10
    assert enterprise["missing_count"] >= 5


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
    assert "Intelligence Console" in response.text or "Company Intelligence" in response.text


def test_new_api_endpoints_exist():
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

    # Test enterprise-readiness endpoint
    er_response = client.get("/enterprise-readiness")
    assert er_response.status_code == 200
    er_payload = er_response.json()
    assert "readiness_level" in er_payload
    assert er_payload["prototype_ready"] is True

    # Test observability endpoints
    obs_metrics = client.get("/observability/metrics")
    assert obs_metrics.status_code == 200
    assert "metrics" in obs_metrics.json()

    obs_evals = client.get("/observability/eval-history")
    assert obs_evals.status_code == 200

    obs_quality = client.get("/observability/quality-report")
    assert obs_quality.status_code == 200

    obs_traces = client.get("/observability/traces")
    assert obs_traces.status_code == 200


# Root and package web assets must stay byte-for-byte identical.
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
