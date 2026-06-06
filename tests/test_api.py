import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from decision_system.api.app import app
from decision_system.cli import app as cli_app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    docs_dir = tmp_path / "company_docs"
    store_dir = tmp_path / "chroma"
    docs_dir.mkdir()
    (docs_dir / "billing.md").write_text(
        "Billing migration requires rollback planning. LegacyAuth owned by Platform Team.",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DECISION_DOCS_DIR", str(docs_dir))
    monkeypatch.setenv("DECISION_STORE_DIR", str(store_dir))
    monkeypatch.setenv("DECISION_COLLECTION", f"api_chunks_{uuid4().hex}")
    monkeypatch.setenv("DECISION_PROVIDER", "fake")
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    monkeypatch.delenv("NVIDIA_NIM_MODEL", raising=False)
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    return TestClient(app, raise_server_exceptions=False)


def test_health_reports_local_backend(client):
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "decision-system-api"
    assert payload["auth"] == "none"
    assert payload["database"] == "none"


def test_documents_index_inspect_and_ask_return_structured_json(client):
    index_response = client.post("/documents/index", json={})
    inspect_response = client.get("/documents/index/inspect")
    ask_response = client.post(
        "/ask",
        json={"question": "Should we migrate billing?", "top_k": 3},
    )

    assert index_response.status_code == 200
    indexed = index_response.json()
    assert indexed["run_id"]
    assert indexed["status"] == "completed"
    assert indexed["data"]["document_count"] == 1
    assert indexed["data"]["chunk_count"] >= 1

    assert inspect_response.status_code == 200
    inspected = inspect_response.json()
    assert inspected["status"] == "ok"
    assert inspected["data"]["chunk_count"] >= 1
    assert "billing.md" in inspected["data"]["source_filenames"]

    assert ask_response.status_code == 200
    asked = ask_response.json()
    assert asked["run_id"]
    assert asked["question"] == "Should we migrate billing?"
    assert asked["report"]["markdown"].startswith("# Decision Report")
    assert asked["data"]["claims"]
    assert asked["data"]["retrieved_evidence"][0]["source_filename"] == "billing.md"


def test_context_and_orchestration_endpoints(client):
    context_response = client.post(
        "/context/build",
        json={"question": "Where are we losing money?"},
    )
    analyze_response = client.post(
        "/orchestration/analyze",
        json={"question": "Where are we losing money?"},
    )
    run_response = client.post(
        "/orchestration/run",
        json={"question": "Where are we losing money?"},
    )

    assert context_response.status_code == 200
    context_payload = context_response.json()
    assert context_payload["run_id"]
    assert context_payload["data"]["question"] == "Where are we losing money?"
    assert "financial" in context_payload["data"]["relevant_data_categories"]

    assert analyze_response.status_code == 200
    analysis_payload = analyze_response.json()
    assert analysis_payload["run_id"]
    assert analysis_payload["data"]["decision_type"] == "financial"
    assert "profile-data" in analysis_payload["data"]["required_tools"]

    assert run_response.status_code == 200
    run_payload = run_response.json()
    assert run_payload["run_id"]
    assert run_payload["status"] == "completed"
    assert run_payload["data"]["decision_type"] == "financial"
    assert run_payload["data"]["saved_path"]


def test_war_room_plan_run_and_latest(client):
    plan_response = client.post(
        "/war-room/plan",
        json={"question": "Where are we losing money?"},
    )
    run_response = client.post(
        "/war-room/run",
        json={"question": "Where are we losing money?"},
    )
    latest_response = client.get("/war-room/latest")

    assert plan_response.status_code == 200
    plan_payload = plan_response.json()
    assert plan_payload["run_id"]
    assert "financial_analyst" in plan_payload["data"]["dispatch_order"]

    assert run_response.status_code == 200
    run_payload = run_response.json()
    assert run_payload["run_id"]
    assert run_payload["status"] == "completed"
    assert run_payload["data"]["workspace"]["artifacts"]

    assert latest_response.status_code == 200
    latest_payload = latest_response.json()
    assert latest_payload["run_id"] == run_payload["run_id"]
    assert latest_payload["data"]["question"] == "Where are we losing money?"


def test_ontology_insights_and_eval_endpoints(client):
    ontology_map_response = client.post("/ontology/map", json={})
    ontology_response = client.get("/ontology")
    detect_response = client.post("/insights/detect", json={})
    insights_response = client.get("/insights")
    war_eval_response = client.post("/evals/war-room", json={})
    provider_eval_response = client.post("/evals/providers", json={"provider": "fake"})

    assert ontology_map_response.status_code == 200
    assert ontology_map_response.json()["data"]["concept_count"] >= 1

    assert ontology_response.status_code == 200
    assert ontology_response.json()["data"]["concepts"]

    assert detect_response.status_code == 200
    assert "insight_count" in detect_response.json()["data"]

    assert insights_response.status_code == 200
    assert "insights" in insights_response.json()["data"]

    assert war_eval_response.status_code == 200
    assert war_eval_response.json()["data"]["failed_cases"] == 0

    assert provider_eval_response.status_code == 200
    provider_payload = provider_eval_response.json()
    assert provider_payload["data"]["provider_name"] == "fake"
    assert provider_payload["data"]["failed_cases"] == 0


def test_api_errors_use_consistent_shape_without_tracebacks(client):
    validation_response = client.post("/ask", json={})
    provider_response = client.post(
        "/ask",
        json={"question": "Should we migrate billing?", "provider": "nvidia_nim"},
    )

    assert validation_response.status_code == 422
    validation_payload = validation_response.json()
    assert validation_payload["error"]["code"] == "validation_error"
    assert "question" in json.dumps(validation_payload["error"]["details"])
    assert "Traceback" not in validation_response.text

    assert provider_response.status_code == 400
    provider_payload = provider_response.json()
    assert provider_payload["error"]["code"] == "provider_not_ready"
    assert "NVIDIA_API_KEY" in provider_payload["error"]["message"]
    assert "Traceback" not in provider_response.text


def test_serve_api_help_exits_zero():
    result = CliRunner().invoke(cli_app, ["serve-api", "--help"])

    assert result.exit_code == 0
    assert "Run the local FastAPI API" in result.output
    assert "--host" in result.output
    assert "--port" in result.output
