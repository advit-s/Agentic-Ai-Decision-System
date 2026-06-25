"""Deterministic policy checker for the v1.2 security/governance layer.

Runs a suite of local policy checks that validate repo layout, hygiene
rules, and fraud patterns that are hard to enforce with tests alone. All
checks are offline, deterministic, and call no external services.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from decision_system.security.models import PolicyCheck, PolicyCheckResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REPO_ROOT = Path(".").resolve()
_GITIGNORE_PATH = REPO_ROOT / ".gitignore"


def _load_gitignore() -> set[str]:
    if not _GITIGNORE_PATH.exists():
        return set()
    return {
        line.strip()
        for line in _GITIGNORE_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    }


def _is_ignored(path: str, ignore_entries: set[str]) -> bool:
    for entry in ignore_entries:
        if not entry:
            continue
        if path == entry or path.startswith(entry.rstrip("/") + "/"):
            return True
    return False


def _is_tracked(path: Path) -> bool:
    """Best-effort: return True when *path* is tracked by git."""
    try:
        result = __import__("subprocess").run(
            ["git", "ls-files", "--error-unmatch", str(path)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except Exception:
        return True  # treat as tracked when unsure


# ---------------------------------------------------------------------------
# Policy checks
# ---------------------------------------------------------------------------


def _check_fake_provider_default() -> PolicyCheck:
    env_example = REPO_ROOT / ".env.example"
    if not env_example.exists():
        return PolicyCheck(
            check_id="fake-provider-default",
            name="Fake provider is default",
            passed=False,
            severity="critical",
            message=".env.example is missing",
            recommendation="Create .env.example with DECISION_PROVIDER=fake",
        )
    text = env_example.read_text(encoding="utf-8")
    found = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#") or not stripped:
            continue
        if stripped.startswith("DECISION_PROVIDER="):
            found = True
            value = stripped.split("=", 1)[1].strip()
            if value.lower() == "fake":
                return PolicyCheck(
                    check_id="fake-provider-default",
                    name="Fake provider is default",
                    passed=True,
                    severity="info",
                    message="DECISION_PROVIDER=fake in .env.example",
                )
            return PolicyCheck(
                check_id="fake-provider-default",
                name="Fake provider is default",
                passed=False,
                severity="critical",
                message=f"DECISION_PROVIDER={value} (expected 'fake')",
                recommendation="Change DECISION_PROVIDER to 'fake'",
            )
    if not found:
        return PolicyCheck(
            check_id="fake-provider-default",
            name="Fake provider is default",
            passed=False,
            severity="critical",
            message="DECISION_PROVIDER not set in .env.example",
            recommendation="Add DECISION_PROVIDER=fake to .env.example",
        )
    # Should not reach here, but fallback
    return PolicyCheck(
        check_id="fake-provider-default",
        name="Fake provider is default",
        passed=False,
        severity="critical",
        message="DECISION_PROVIDER not set in .env.example",
        recommendation="Add DECISION_PROVIDER=fake to .env.example",
    )


def _check_generated_dirs_ignored() -> PolicyCheck:
    ignore_entries = _load_gitignore()
    required = [
        ".decision_system/",
        ".decision_system/workspaces/",
        ".decision_system/connectors/",
        ".decision_system/security/",
        "datasets/",
        "__pycache__/",
        ".pytest_cache/",
        "evals/results/*.json",
    ]
    missing = [r for r in required if not _is_ignored(r, ignore_entries)]
    if not missing:
        return PolicyCheck(
            check_id="generated-dirs-ignored",
            name="Generated directories are ignored",
            passed=True,
            severity="info",
            message="All required ignore rules present in .gitignore",
        )
    return PolicyCheck(
        check_id="generated-dirs-ignored",
        name="Generated directories are ignored",
        passed=False,
        severity="warning",
        message=f"Missing ignore rules: {', '.join(missing)}",
        recommendation="Add missing paths to .gitignore",
    )


def _check_env_not_tracked() -> PolicyCheck:
    for name in (".env", ".env.local", ".env.*.local"):
        if (REPO_ROOT / name).exists():
            if _is_tracked(REPO_ROOT / name):
                return PolicyCheck(
                    check_id="env-not-tracked",
                    name="No .env files are tracked",
                    passed=False,
                    severity="critical",
                    message=f"{name} exists and is tracked by git",
                    recommendation=f"Remove {name} from git and add to .gitignore",
                )
    return PolicyCheck(
        check_id="env-not-tracked",
        name="No .env files are tracked",
        passed=True,
        severity="info",
        message="No .env files tracked by git",
    )


def _check_connector_stubs_no_network() -> PolicyCheck:
    stub_file = REPO_ROOT / "src/decision_system/connectors/stubs.py"
    if not stub_file.exists():
        return PolicyCheck(
            check_id="connector-stubs-no-network",
            name="Connector stubs do not make network calls",
            passed=True,
            severity="info",
            message="Stub file not present (connectors are stubs or real)",
        )
    text = stub_file.read_text(encoding="utf-8")
    violations = []
    for pattern in ("requests.", "httpx.", "urllib", "http.client", "socket."):
        if pattern in text:
            violations.append(pattern)
    if violations:
        return PolicyCheck(
            check_id="connector-stubs-no-network",
            name="Connector stubs do not make network calls",
            passed=False,
            severity="critical",
            message=f"Potential network patterns found: {', '.join(violations)}",
            recommendation="Remove network calls from connector stubs",
        )
    return PolicyCheck(
        check_id="connector-stubs-no-network",
        name="Connector stubs do not make network calls",
        passed=True,
        severity="info",
        message="No obvious network patterns in connector stubs",
    )


def _check_secrets_in_source() -> PolicyCheck:
    """Lightweight check: no obviously leaked full secrets in tracked Python/source files."""
    secrets: list[str] = []
    try:
        for file_path in REPO_ROOT.rglob("*.py"):
            # Skip the security package itself - it contains regex patterns
            # like "sk-" and "nvapi-" that are meant to DETECT secrets
            # Skip test files that use synthetic fake secret values
            rel_parts = file_path.relative_to(REPO_ROOT).parts
            fname = file_path.name
            # Check the whole path for "security" since the package lives under
            # src/decision_system/security/, not at the repo root.
            if rel_parts and ("security" in rel_parts or ".decision_system" in rel_parts):
                continue
            if fname.startswith("test_") and "security" in fname:
                continue
            try:
                text = file_path.read_text(encoding="utf-8", errors="replace")
                # Look for actual API key values, not regex patterns
                # sk-<20+ chars> and nvapi-<20+ chars> at start of word
                import re as _re

                if _re.search(r"\bsk-[A-Za-z0-9\-]{8,}\b", text):
                    secrets.append(str(file_path.relative_to(REPO_ROOT)))
                elif _re.search(r"\bnvapi-[A-Za-z0-9\-_]{20,}\b", text):
                    secrets.append(str(file_path.relative_to(REPO_ROOT)))
                elif _re.search(r"(?:AKIA|ASIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA)[0-9A-Z]{16}", text):
                    secrets.append(str(file_path.relative_to(REPO_ROOT)))
            except (OSError, PermissionError):
                continue
    except (OSError, PermissionError):
        pass
    if secrets:
        return PolicyCheck(
            check_id="secrets-in-source",
            name="No obvious secrets in tracked source files",
            passed=False,
            severity="critical",
            message=f"Potential secret-like patterns in: {', '.join(secrets)}",
            recommendation="Remove secrets and use environment variables",
        )
    return PolicyCheck(
        check_id="secrets-in-source",
        name="No obvious secrets in tracked source files",
        passed=True,
        severity="info",
        message="No obviously leaked secrets found in tracked source files",
    )


def _check_agent_docs_exist() -> PolicyCheck:
    missing = []
    for name in ("AGENTS.md", "CLAUDE.md"):
        if not (REPO_ROOT / name).exists():
            missing.append(name)
    if missing:
        return PolicyCheck(
            check_id="agent-docs-exist",
            name="Agent instruction files exist",
            passed=False,
            severity="warning",
            message=f"Missing: {', '.join(missing)}",
            recommendation="Add the missing agent instruction files",
        )
    return PolicyCheck(
        check_id="agent-docs-exist",
        name="Agent instruction files exist",
        passed=True,
        severity="info",
        message="AGENTS.md and CLAUDE.md present",
    )


def _check_release_checklist_exists() -> PolicyCheck:
    path = REPO_ROOT / "docs" / "RELEASE_CHECKLIST.md"
    if not path.exists():
        return PolicyCheck(
            check_id="release-checklist-exists",
            name="Release checklist exists",
            passed=False,
            severity="warning",
            message="docs/RELEASE_CHECKLIST.md not found",
            recommendation="Add a release checklist document",
        )
    return PolicyCheck(
        check_id="release-checklist-exists",
        name="Release checklist exists",
        passed=True,
        severity="info",
        message="docs/RELEASE_CHECKLIST.md present",
    )


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

_ALL_CHECKS = [
    _check_fake_provider_default,
    _check_generated_dirs_ignored,
    _check_env_not_tracked,
    _check_connector_stubs_no_network,
    _check_secrets_in_source,
    _check_agent_docs_exist,
    _check_release_checklist_exists,
]


def run_policy_checks() -> PolicyCheckResult:
    """Run all policy checks and return the aggregated result."""
    checks = [fn() for fn in _ALL_CHECKS]
    passed = sum(1 for c in checks if c.passed)
    warnings = sum(1 for c in checks if not c.passed and c.severity == "warning")
    failed = sum(1 for c in checks if not c.passed and c.severity in ("critical",))
    if failed:
        status: Literal["ok", "warn", "fail"] = "fail"
    elif warnings:
        status = "warn"
    else:
        status = "ok"
    return PolicyCheckResult(
        checks=checks,
        passed_count=passed,
        warning_count=warnings,
        failed_count=failed,
        overall_status=status,
    )
