import json
from uuid import uuid4

import pytest
from typer.testing import CliRunner

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
    from decision_system.api.app import set_scheduler_enabled
    set_scheduler_enabled(False)
    from decision_system.api.app import app
    from httpx import ASGITransport
    import httpx
    transport = ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")


class TestHealth:
    async def test_health(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    async def test_health_version(self, client):
        resp = await client.get("/health")
        v = resp.json()["version"]
        from decision_system import __version__
        assert v == __version__


class TestProviders:
    async def test_list_providers(self, client):
        resp = await client.get("/providers")
        data = resp.json()
        assert isinstance(data, dict)

    async def test_default_provider(self, client):
        resp = await client.get("/providers/default")
        data = resp.json()
        # May be None in default config or a dict
        if data is not None:
            assert isinstance(data, dict)
