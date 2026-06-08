"""Tests for v1.2 Security, Governance, and Audit package.

All secrets in tests are synthetic. No external services or API keys required.
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from decision_system.security.models import (
    ApprovalRequest,
    ApprovalStatus,
    AuditEvent,
    PolicyCheck,
    PolicyCheckResult,
    RedactionFinding,
    RedactionPreviewResult,
    SecretFinding,
    SecretScanResult,
)
from decision_system.security.audit import (
    append_event,
    event_counts,
    load_events,
    render_audit_log,
)
from decision_system.security.redaction import redact
from decision_system.security.secret_scan import (
    DEFAULT_SCAN_DIRS,
    DEFAULT_SCAN_ROOT,
    _mask_text,
)
from decision_system.security.approvals import (
    create_approval,
    inspect_approval,
    list_approvals,
    update_approval_status,
)
from decision_system.security.policy import run_policy_checks
from decision_system.security import approvals as _approval_mod
from decision_system.security import policy as _policy_mod


# ================================================================
# Models
# ================================================================


class TestModels:
    def test_secret_finding(self) -> None:
        f = SecretFinding(
            finding_id="f1", source_path="a.py", line_number=1,
            secret_type="api_key", severity="high",
            matched_preview="sk-******test", recommendation="rotate it",
        )
        assert f.created_at
        assert f.severity == "high"

    def test_secret_scan_result(self) -> None:
        r = SecretScanResult(
            scan_id="s1", scanned_path=".", files_scanned=0,
            files_skipped=0, findings=[], overall_status="ok",
        )
        assert r.findings == []

    def test_redaction_finding(self) -> None:
        f = RedactionFinding(
            text_type="email", start=0, end=10,
            matched_preview="a@b.com", replacement="[EMAIL]", confidence="high",
        )
        assert f.text_type == "email"

    def test_redaction_preview_result(self) -> None:
        r = RedactionPreviewResult(
            original_text="a@b.com", redacted_text="[EMAIL]",
            findings=[], finding_count=1,
        )
        assert r.original_text == "a@b.com"

    def test_audit_event(self) -> None:
        ev = AuditEvent(event_id="e1", event_type="t", message="m")
        assert ev.actor == "local-user"
        assert ev.metadata == {}

    def test_policy_check(self) -> None:
        c = PolicyCheck(check_id="c1", name="t", passed=True,
                        severity="critical", message="ok", recommendation="")
        assert c.passed is True

    def test_approval_request_defaults(self) -> None:
        req = ApprovalRequest(approval_id="r1", reason="testing")
        assert req.status == "pending"
        assert req.requested_by == "local-user"
        assert req.metadata == {}
        assert req.resolved_at is None


# ================================================================
# _mask_text
# ================================================================


class TestMaskText:
    def test_short_strings(self) -> None:
        assert _mask_text("") == ""
        assert _mask_text("1") == "*"
        assert _mask_text("1234") == "****"
        assert _mask_text("1234567") == "*******"

    def test_eight_chars(self) -> None:
        assert _mask_text("12345678") == "********"

    def test_normal_string(self) -> None:
        masked = _mask_text("sk-1234567890abcdef")
        assert masked.startswith("sk-1")
        assert masked.endswith("cdef")
        assert "****" in masked

    def test_non_alphanumeric(self) -> None:
        masked = _mask_text("." * 20)
        assert masked.startswith("." * 4)
        assert masked.endswith("." * 4)


# ================================================================
# Secret scanning
# ================================================================


class TestSecretScanning:
    def _patch_scan(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> object:
        """Patch _IGNORE_DIRS so the scanner checks the tmp dir without skipping:
        Binary files / files matching __pycache__/ etc. are intentionally skipped
        because they have non-text extensions."""
        import decision_system.security.secret_scan as _scan_mod

        monkeypatch.setattr(_scan_mod, "DEFAULT_SCAN_ROOT", str(tmp_path))
        # Only skip __pycache__ and pyc but NOT .decision_system, .git, etc.
        # files inside __pycache__ are skipped by extension (binaries).
        monkeypatch.setattr(_scan_mod, "_IGNORE_DIRS", frozenset())
        return _scan_mod

    def test_empty_dir(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _scan_mod = self._patch_scan(tmp_path, monkeypatch)
        result = _scan_mod.scan_repo(str(tmp_path))
        assert result.findings == []
        assert result.overall_status == "ok"

    def test_detects_env_secret(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._patch_scan(tmp_path, monkeypatch)
        (tmp_path / ".env").write_text(
            "OPENAI_API_KEY=sk-1234567890abcdef012345\n", encoding="utf-8"
        )
        import decision_system.security.secret_scan as _scan_mod
        result = _scan_mod.scan_repo(str(tmp_path))
        assert len(result.findings) >= 1
        env_findings = [f for f in result.findings if f.secret_type == "env_file"]
        api_findings = [f for f in result.findings if f.secret_type == "api_key"]
        assert len(env_findings) >= 1 or len(api_findings) >= 1
        if env_findings:
            assert env_findings[0].severity == "critical"
            assert "sk-1234567890" not in env_findings[0].matched_preview

    def test_detects_generic_secret(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._patch_scan(tmp_path, monkeypatch)
        (tmp_path / "config.py").write_text(
            'PASSWORD = "hunter2"\n', encoding="utf-8"
        )
        import decision_system.security.secret_scan as _scan_mod
        result = _scan_mod.scan_repo(str(tmp_path))
        assert len(result.findings) >= 1
        f = result.findings[0]
        assert f.secret_type == "other"

    def test_detects_sk_prefix(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._patch_scan(tmp_path, monkeypatch)
        (tmp_path / "keys.py").write_text(
            'api_key = "sk-mySecretKey1234567890abcdef"\n', encoding="utf-8"
        )
        import decision_system.security.secret_scan as _scan_mod
        result = _scan_mod.scan_repo(str(tmp_path))
        assert len(result.findings) >= 1
        f = result.findings[0]
        assert f.secret_type == "api_key"
        assert f.severity == "high"

    def test_detects_aws_key(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._patch_scan(tmp_path, monkeypatch)
        (tmp_path / "aws.py").write_text(
            'key = "AKIAIOSFODNN7EXAMPLE"\n', encoding="utf-8"
        )
        import decision_system.security.secret_scan as _scan_mod
        result = _scan_mod.scan_repo(str(tmp_path))
        assert len(result.findings) >= 1
        f = result.findings[0]
        assert f.secret_type == "aws_key"

    def test_detects_token(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._patch_scan(tmp_path, monkeypatch)
        (tmp_path / "auth.py").write_text(
            'token = "abcdefghijklmnopqrstuvwxyz"\n', encoding="utf-8"
        )
        import decision_system.security.secret_scan as _scan_mod
        result = _scan_mod.scan_repo(str(tmp_path))
        assert len(result.findings) >= 1
        f = result.findings[0]
        assert f.secret_type == "token"

    def test_detects_nvapi_prefix(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._patch_scan(tmp_path, monkeypatch)
        (tmp_path / "nvidia.py").write_text(
            'key = "nvapi-myVeryLongSecretKey1234567890abc"\n', encoding="utf-8"
        )
        import decision_system.security.secret_scan as _scan_mod
        result = _scan_mod.scan_repo(str(tmp_path))
        assert len(result.findings) >= 1
        f = result.findings[0]
        assert f.secret_type == "api_key"

    def test_no_full_value_in_preview(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._patch_scan(tmp_path, monkeypatch)
        real_key = "sk-1234567890abcdef01234567"
        (tmp_path / "leaky.py").write_text(
            f'key = "{real_key}"\n', encoding="utf-8"
        )
        import decision_system.security.secret_scan as _scan_mod
        result = _scan_mod.scan_repo(str(tmp_path))
        assert len(result.findings) >= 1
        assert real_key not in result.findings[0].matched_preview

    def test_status_warn_with_findings(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._patch_scan(tmp_path, monkeypatch)
        (tmp_path / "leak.py").write_text(
            'token = "abcdefghijklmnopqrstuvwxyz"\n', encoding="utf-8"
        )
        import decision_system.security.secret_scan as _scan_mod
        result = _scan_mod.scan_repo(str(tmp_path))
        assert result.overall_status == "warn"

    def test_source_path_and_line_number(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._patch_scan(tmp_path, monkeypatch)
        (tmp_path / "leak.py").write_text(
            "# comment\ntoken = 'abcdefghijklmnopqrstuv'\n",
            encoding="utf-8",
        )
        import decision_system.security.secret_scan as _scan_mod
        result = _scan_mod.scan_repo(str(tmp_path))
        f = result.findings[0]
        assert "leak.py" in f.source_path
        assert f.line_number == 2

    def test_skips_binary_files(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._patch_scan(tmp_path, monkeypatch)
        (tmp_path / "image.png").write_bytes(b"PK\x00\x01\x02")
        import decision_system.security.secret_scan as _scan_mod
        result = _scan_mod.scan_repo(str(tmp_path))
        assert result.findings == []

    def test_commented_env_line_skipped(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._patch_scan(tmp_path, monkeypatch)
        (tmp_path / ".env").write_text(
            "# OPENAI_API_KEY=sk-real-key-should-not-match\n",
            encoding="utf-8",
        )
        import decision_system.security.secret_scan as _scan_mod
        result = _scan_mod.scan_repo(str(tmp_path))
        env_findings = [f for f in result.findings if f.secret_type == "env_file"]
        assert len(env_findings) == 0


# ================================================================
# Redaction
# ================================================================


class TestRedaction:
    def test_email(self) -> None:
        result = redact("Contact support@example.com for help.")
        assert "[EMAIL]" in result.redacted_text
        assert "@" not in result.redacted_text
        assert result.finding_count >= 1
        assert any(f.text_type == "email" for f in result.findings)

    def test_phone(self) -> None:
        result = redact("Call us at +1 555-123-4567 today.")
        assert "[PHONE]" in result.redacted_text
        assert "555-123-4567" not in result.redacted_text

    def test_secret_token(self) -> None:
        result = redact("Use sk-mySecretKey1234567890 now.")
        assert "[SECRET]" in result.redacted_text
        assert "sk-mySecretKey1234567890" not in result.redacted_text

    def test_customer_id(self) -> None:
        result = redact("Your customer_id=12345 is active.")
        assert "customer_id=[CUSTOMER_ID]" in result.redacted_text
        assert "12345" not in result.redacted_text

    def test_no_input_mutation(self) -> None:
        original = "hello@example.com"
        _ = redact(original)
        assert original == "hello@example.com"

    def test_empty_text(self) -> None:
        result = redact("")
        assert result.redacted_text == ""
        assert result.finding_count == 0

    def test_no_match(self) -> None:
        result = redact("The sky is blue today.")
        assert result.findings == []
        assert result.finding_count == 0

    def test_multiple_findings(self) -> None:
        text = "Email admin@corp.com, phone 555-123-4567."
        result = redact(text)
        assert result.finding_count >= 2
        assert "[EMAIL]" in result.redacted_text
        assert "[PHONE]" in result.redacted_text

    def test_multiple_emails(self) -> None:
        text = "a@x.com and b@y.com"
        result = redact(text)
        assert result.finding_count == 2

    def test_finding_fields(self) -> None:
        result = redact("sk-testkey1234567890abcdef")
        f = result.findings[0]
        assert f.text_type == "secret_token"
        assert f.start >= 0
        assert f.end > f.start

    def test_deterministic(self) -> None:
        text = "sk-testkey1234567890abcdef hello@world.com"
        r1 = redact(text)
        r2 = redact(text)
        assert r1.redacted_text == r2.redacted_text

    def test_returns_model(self) -> None:
        result = redact("test@example.com")
        assert isinstance(result, RedactionPreviewResult)

    def test_offset_correct_email(self) -> None:
        text = "start hello@example.com end"
        result = redact(text)
        emails = [f for f in result.findings if f.text_type == "email"]
        assert len(emails) == 1
        assert text[emails[0].start:emails[0].end] == "hello@example.com"


# ================================================================
# Audit log
# ================================================================


class TestAudit:
    def test_event_defaults(self) -> None:
        ev = AuditEvent(event_id="e1", event_type="t", message="m")
        assert ev.actor == "local-user"
        assert ev.metadata == {}

    def test_roundtrip(self, tmp_path: Path) -> None:
        log_path = tmp_path / "audit.jsonl"
        append_event("test_event", "hello", actor="tester", audit_path=log_path)
        events = load_events(log_path)
        assert len(events) == 1
        assert events[0].event_type == "test_event"

    def test_missing_log_returns_empty(self) -> None:
        assert load_events(Path("/tmp/nonexistent_12345.jsonl")) == []

    def test_malformed_log(self, tmp_path: Path) -> None:
        log_path = tmp_path / "bad.jsonl"
        log_path.write_text(
            "not json\n",
            encoding="utf-8",
        )
        events = load_events(log_path)
        assert len(events) == 0

    def test_limit(self, tmp_path: Path) -> None:
        log_path = tmp_path / "audit.jsonl"
        for i in range(4):
            append_event(f"type{i}", f"msg{i}", audit_path=log_path)
        events = load_events(log_path, limit=2)
        assert len(events) == 2

    def test_event_counts_empty(self) -> None:
        assert event_counts([]) == {}

    def test_event_counts_mixed(self) -> None:
        events = [
            AuditEvent(event_id="e1", event_type="a", actor="u", message=""),
            AuditEvent(event_id="e2", event_type="b", actor="u", message=""),
            AuditEvent(event_id="e3", event_type="a", actor="u", message=""),
        ]
        assert event_counts(events) == {"a": 2, "b": 1}

    def test_render_audit_log_empty(self) -> None:
        rendered = render_audit_log([])
        assert "(no events)" in rendered

    def test_render_audit_log_two_events(self) -> None:
        ev1 = AuditEvent(event_id="e1", event_type="secret_scan_run", actor="u", message="m1")
        ev2 = AuditEvent(event_id="e2", event_type="policy_check_run", actor="u", message="m2")
        rendered = render_audit_log([ev1, ev2])
        assert "Total events: 2" in rendered
        assert "secret_scan_run" in rendered

    def test_render_audit_log_with_limit(self) -> None:
        events = [AuditEvent(event_id=f"e{i}", event_type="x", actor="u", message="")
                  for i in range(20)]
        rendered = render_audit_log(events, limit=5)
        assert "Total events: 20" in rendered


# ================================================================
# Policy checks
# ================================================================


class TestPolicy:
    @pytest.fixture(autouse=True)
    def _configure(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(_policy_mod, "REPO_ROOT", tmp_path)
        monkeypatch.setattr(_policy_mod, "_GITIGNORE_PATH", tmp_path / ".gitignore")

    def _write_gitignore(self, tmp_path: Path) -> None:
        (tmp_path / ".gitignore").write_text(
            "\n".join([
                ".decision_system/",
                ".decision_system/workspaces/",
                ".decision_system/connectors/",
                ".decision_system/security/",
                "datasets/",
                "__pycache__/",
                ".pytest_cache/",
                "evals/results/*.json",
            ]) + "\n",
            encoding="utf-8",
        )

    def test_all_checks_run(self, tmp_path: Path) -> None:
        (tmp_path / ".env.example").write_text("DECISION_PROVIDER=fake\n", encoding="utf-8")
        result = run_policy_checks()
        assert len(result.checks) == 7

    def test_check_ids_match(self, tmp_path: Path) -> None:
        (tmp_path / ".env.example").write_text("DECISION_PROVIDER=fake\n", encoding="utf-8")
        result = run_policy_checks()
        check_ids = {c.check_id for c in result.checks}
        expected = {
            "fake-provider-default",
            "generated-dirs-ignored",
            "env-not-tracked",
            "connector-stubs-no-network",
            "secrets-in-source",
            "agent-docs-exist",
            "release-checklist-exists",
        }
        assert check_ids == expected

    def test_fake_provider_default_passes(self, tmp_path: Path) -> None:
        (tmp_path / ".env.example").write_text("DECISION_PROVIDER=fake\n", encoding="utf-8")
        result = run_policy_checks()
        c = [x for x in result.checks if x.check_id == "fake-provider-default"][0]
        assert c.passed is True

    def test_fake_provider_default_missing(self, tmp_path: Path) -> None:
        result = run_policy_checks()
        c = [x for x in result.checks if x.check_id == "fake-provider-default"][0]
        assert c.passed is False
        assert c.severity == "critical"

    def test_fake_provider_default_wrong(self, tmp_path: Path) -> None:
        (tmp_path / ".env.example").write_text("DECISION_PROVIDER=openai\n", encoding="utf-8")
        result = run_policy_checks()
        c = [x for x in result.checks if x.check_id == "fake-provider-default"][0]
        assert c.passed is False
        assert "openai" in c.message

    def test_generated_dirs_ignored_pass(self, tmp_path: Path) -> None:
        self._write_gitignore(tmp_path)
        (tmp_path / ".env.example").write_text("DECISION_PROVIDER=fake\n", encoding="utf-8")
        result = run_policy_checks()
        c = [x for x in result.checks if x.check_id == "generated-dirs-ignored"][0]
        assert c.passed is True

    def test_env_not_tracked_pass(self, tmp_path: Path) -> None:
        (tmp_path / ".env.example").write_text("DECISION_PROVIDER=fake\n", encoding="utf-8")
        result = run_policy_checks()
        c = [x for x in result.checks if x.check_id == "env-not-tracked"][0]
        assert c.passed is True

    def test_agent_docs_exist_pass(self, tmp_path: Path) -> None:
        self._write_gitignore(tmp_path)
        (tmp_path / ".env.example").write_text("DECISION_PROVIDER=fake\n", encoding="utf-8")
        (tmp_path / "AGENTS.md").write_text("# x\n", encoding="utf-8")
        (tmp_path / "CLAUDE.md").write_text("# x\n", encoding="utf-8")
        result = run_policy_checks()
        c = [x for x in result.checks if x.check_id == "agent-docs-exist"][0]
        assert c.passed is True

    def test_agent_docs_exist_fail(self, tmp_path: Path) -> None:
        self._write_gitignore(tmp_path)
        (tmp_path / ".env.example").write_text("DECISION_PROVIDER=fake\n", encoding="utf-8")
        result = run_policy_checks()
        c = [x for x in result.checks if x.check_id == "agent-docs-exist"][0]
        assert c.passed is False
        assert c.severity == "warning"

    def test_all_checks_pass(self, tmp_path: Path) -> None:
        self._write_gitignore(tmp_path)
        (tmp_path / ".env.example").write_text("DECISION_PROVIDER=fake\n", encoding="utf-8")
        (tmp_path / "AGENTS.md").write_text("# x\n", encoding="utf-8")
        (tmp_path / "CLAUDE.md").write_text("# x\n", encoding="utf-8")
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "RELEASE_CHECKLIST.md").write_text("x\n", encoding="utf-8")
        result = run_policy_checks()
        assert result.overall_status == "ok"
        assert result.passed_count == 7

    def test_aggregation_counts(self, tmp_path: Path) -> None:
        self._write_gitignore(tmp_path)
        (tmp_path / ".env.example").write_text("DECISION_PROVIDER=fake\n", encoding="utf-8")
        result = run_policy_checks()
        assert result.passed_count + result.failed_count + result.warning_count == len(result.checks)

    def test_secrets_in_source_no_false_positive(self, tmp_path: Path) -> None:
        self._write_gitignore(tmp_path)
        (tmp_path / ".env.example").write_text("DECISION_PROVIDER=fake\n", encoding="utf-8")
        sec_dir = tmp_path / "src" / "decision_system" / "security"
        sec_dir.mkdir(parents=True)
        (sec_dir / "secret_scan.py").write_text(
            textwrap.dedent(
                r'''
                _PATTERNS = [
                    (r"(?i)\bsk-[A-Za-z0-9]{20,}\b", "sk_prefix"),
                    (r"(?i)\bnvapi-[A-Za-z0-9\-_]{20,}\b", "nvapi_prefix"),
                ]
                '''
            ),
            encoding="utf-8",
        )
        result = run_policy_checks()
        c = [x for x in result.checks if x.check_id == "secrets-in-source"][0]
        assert c.passed is True

    def test_secrets_in_source_detects_leak(self, tmp_path: Path) -> None:
        self._write_gitignore(tmp_path)
        (tmp_path / ".env.example").write_text("DECISION_PROVIDER=fake\n", encoding="utf-8")
        (tmp_path / "leaked.py").write_text(
            'key = "sk-my-real-api-key-1234567890abcdefghijk"\n',
            encoding="utf-8",
        )
        result = run_policy_checks()
        c = [x for x in result.checks if x.check_id == "secrets-in-source"][0]
        assert c.passed is False
        assert "leaked.py" in c.message


# ================================================================
# Approvals store
# ================================================================


class TestApprovals:
    @pytest.fixture(autouse=True)
    def _isolate(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(_policy_mod, "REPO_ROOT", tmp_path)

    def test_create(self) -> None:
        req = create_approval(reason="integration-test", requested_by="tester")
        assert req.approval_id
        assert req.status == "pending"
        assert req.reason == "integration-test"

    def test_create_with_metadata(self) -> None:
        req = create_approval(reason="test", requested_by="u",
                               metadata={"source": "suite"})
        assert req.metadata == {"source": "suite"}

    def test_list_empty(self) -> None:
        assert list_approvals() == []

    def test_list_returns_all(self) -> None:
        create_approval("a")
        create_approval("b")
        assert len(list_approvals()) == 2

    def test_status_lifecycle(self) -> None:
        r1 = create_approval("req-1")
        r2 = create_approval("req-2")
        r1_updated = update_approval_status(r1.approval_id, "approved")
        assert r1_updated.status == "approved"

        pending = list_approvals(status_filter="pending")
        assert len(pending) == 1
        assert pending[0].approval_id == r2.approval_id
