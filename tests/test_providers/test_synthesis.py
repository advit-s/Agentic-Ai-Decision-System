"""Tests for synthesis parser, prompts, and service."""

from __future__ import annotations

import pytest

from decision_system.synthesis import (
    SYNTHESIS_MODES,
    get_template,
    parse_synthesis_output,
    DraftClaim,
    run_synthesis,
)


class TestPromptTemplates:
    def test_all_modes_have_templates(self):
        for mode in ["summary", "risks", "opportunities", "claims", "report_outline"]:
            template = get_template(mode)  # type: ignore
            assert template["mode"] == mode
            assert "system" in template
            assert "user" in template

    def test_template_has_anti_hallucination(self):
        template = get_template("summary")
        system = template["system"]
        assert "Use ONLY the provided evidence" in system
        assert "Do not invent" in system

    def test_template_has_placeholders(self):
        template = get_template("summary")
        user = template["user"]
        assert "{evidence}" in user
        assert "{question}" in user

    def test_claims_template_requests_json(self):
        template = get_template("claims")
        assert "JSON" in template["user"]
        assert "claim_text" in template["user"]

    def test_template_version(self):
        from decision_system.synthesis.prompts import TEMPLATE_VERSION
        assert TEMPLATE_VERSION == "1.0.0"


class TestOutputParser:
    def test_parse_valid_json_array(self):
        raw = '[{"claim_text": "Test claim", "claim_type": "fact", "confidence": 0.9}]'
        result = parse_synthesis_output(raw)
        assert result.success is True
        assert len(result.draft_claims) == 1
        assert result.draft_claims[0].claim_text == "Test claim"

    def test_parse_json_object_with_claims(self):
        raw = '{"summary": "Test summary", "claims": [{"claim_text": "C1", "claim_type": "risk", "confidence": 0.8}]}'
        result = parse_synthesis_output(raw)
        assert result.success is True
        assert result.summary_text == "Test summary"
        assert len(result.draft_claims) == 1

    def test_parse_markdown_fenced_json(self):
        raw = 'Some text\n```json\n[{"claim_text": "Fenced claim", "claim_type": "fact", "confidence": 0.7}]\n```\nMore text'
        result = parse_synthesis_output(raw)
        assert result.success is True
        assert result.parse_mode == "markdown_fence"
        assert len(result.draft_claims) == 1
        assert result.draft_claims[0].claim_text == "Fenced claim"

    def test_parse_code_fence_no_language(self):
        raw = '```\n{"summary": "Code fence summary"}\n```'
        result = parse_synthesis_output(raw)
        assert result.success is True
        assert result.parse_mode == "code_fence"
        assert "Code fence summary" in result.summary_text

    def test_parse_plain_text_fallback(self):
        raw = "This is a plain text response without any JSON structure."
        result = parse_synthesis_output(raw)
        assert result.success is False
        assert result.parse_mode == "plain_text"
        assert result.summary_text == raw
        assert len(result.warnings) > 0
        assert len(result.draft_claims) == 0

    def test_parse_empty_text(self):
        result = parse_synthesis_output("")
        assert result.success is False
        assert len(result.warnings) > 0

    def test_parse_invalid_json(self):
        result = parse_synthesis_output("{invalid json here}")
        assert result.success is False
        assert result.parse_mode == "plain_text"

    def test_parse_malformed_claims_skipped(self):
        raw = '[{"claim_text": "Valid", "claim_type": "fact", "confidence": 0.5}, "not a claim object"]'
        result = parse_synthesis_output(raw)
        assert result.success is True
        assert len(result.draft_claims) == 1
        assert result.draft_claims[0].claim_text == "Valid"

    def test_parse_summary_text_only(self):
        raw = '{"summary_text": "Just a summary"}'
        result = parse_synthesis_output(raw)
        assert result.success is True
        assert result.summary_text == "Just a summary"
        assert len(result.draft_claims) == 0

    def test_draft_claim_model(self):
        claim = DraftClaim(
            claim_text="Test",
            claim_type="risk",
            confidence=0.85,
            evidence_ids=["ev-1"],
            evidence_snippets=["supporting text"],
        )
        d = claim.model_dump()
        assert d["claim_text"] == "Test"
        assert d["claim_type"] == "risk"
        assert d["confidence"] == 0.85


class TestSynthesisService:
    def test_no_provider_returns_warning(self):
        result = run_synthesis(
            workspace_id="ws-test",
            question="What are the risks?",
            evidence_results=[],
        )
        assert result.synthesis_id.startswith("syn-")
        assert len(result.warnings) > 0
        assert result.summary_text == ""
        assert result.draft_claims == []

    def test_with_fake_provider(self):
        import os, tempfile
        tmp = tempfile.mkdtemp()
        old_data_dir = os.environ.get("DECISION_SYSTEM_DATA_DIR")
        os.environ["DECISION_SYSTEM_DATA_DIR"] = tmp
        try:
            from decision_system.providers.store import create_provider
            from decision_system.providers.models import ProviderCreateRequest
            req = ProviderCreateRequest(name="Synth Fake", provider_type="fake")
            config = create_provider(req)

            result = run_synthesis(
                workspace_id="ws-test",
                question="Summarize the evidence",
                evidence_results=[
                    {"id": "ev-1", "text": "Billing migration requires rollback planning."},
                    {"id": "ev-2", "text": "LegacyAuth is owned by Platform Team."},
                ],
                provider_config=config,
                synthesis_mode="summary",
            )
            assert result.synthesis_id.startswith("syn-")
            assert len(result.summary_text) > 0
            assert "evidence" in result.summary_text.lower() or len(result.summary_text) > 20
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)
            if old_data_dir is not None:
                os.environ["DECISION_SYSTEM_DATA_DIR"] = old_data_dir
            else:
                os.environ.pop("DECISION_SYSTEM_DATA_DIR", None)

    def test_claims_mode_with_fake_provider(self):
        import os, tempfile
        tmp = tempfile.mkdtemp()
        old_data_dir = os.environ.get("DECISION_SYSTEM_DATA_DIR")
        os.environ["DECISION_SYSTEM_DATA_DIR"] = tmp
        try:
            from decision_system.providers.store import create_provider
            from decision_system.providers.models import ProviderCreateRequest
            req = ProviderCreateRequest(name="Synth Claims", provider_type="fake")
            config = create_provider(req)

            result = run_synthesis(
                workspace_id="ws-test",
                question="Extract claims from evidence",
                evidence_results=[
                    {"id": "ev-1", "text": "Billing migration requires rollback planning."},
                ],
                provider_config=config,
                synthesis_mode="claims",
            )
            assert result.synthesis_id.startswith("syn-")
            assert len(result.summary_text) > 0 or len(result.draft_claims) > 0
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)
            if old_data_dir is not None:
                os.environ["DECISION_SYSTEM_DATA_DIR"] = old_data_dir
            else:
                os.environ.pop("DECISION_SYSTEM_DATA_DIR", None)
