import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

# Disable background scheduler before importing app
from decision_system.api.app import set_scheduler_enabled
set_scheduler_enabled(False)

from decision_system.api.app import app
from decision_system.cli import app as cli_app
from decision_system.provider_eval.runner import DEFAULT_PROVIDER_EVAL_CASES


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
